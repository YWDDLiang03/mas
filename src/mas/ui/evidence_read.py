"""Indexed, task-scoped evidence relationships and saved source context."""
from __future__ import annotations

import hashlib
import json
from typing import Any

from .read_summaries import claim_context, fact_summary, original_context

EVIDENCE_TABLES = ("evidence_links", "claim_origins", "evidence_documents", "evidence_sources")
EVIDENCE_SCHEMA = """
CREATE TABLE IF NOT EXISTS evidence_links(
 task_id TEXT,claim_id TEXT,criterion_ref TEXT,attribute_ref TEXT,rule_ref TEXT,
 candidate_ref TEXT NOT NULL,run_id TEXT NOT NULL,assessment_row INTEGER NOT NULL,
 relationship TEXT,name TEXT,source_row INTEGER,verdict TEXT,via_claim_id TEXT NOT NULL,superseded_row INTEGER,
 PRIMARY KEY(task_id,claim_id,criterion_ref,candidate_ref,run_id,assessment_row,relationship,via_claim_id));
CREATE INDEX IF NOT EXISTS evidence_link_claim ON evidence_links(task_id,claim_id,source_row DESC);
CREATE INDEX IF NOT EXISTS evidence_link_criterion ON evidence_links(task_id,criterion_ref,claim_id);
CREATE INDEX IF NOT EXISTS evidence_link_attribute ON evidence_links(task_id,attribute_ref,claim_id);
CREATE INDEX IF NOT EXISTS evidence_link_rule ON evidence_links(task_id,rule_ref,claim_id);
CREATE INDEX IF NOT EXISTS evidence_link_candidate ON evidence_links(task_id,candidate_ref,claim_id);
CREATE INDEX IF NOT EXISTS evidence_link_assessment ON evidence_links(assessment_row) WHERE assessment_row>0;
CREATE INDEX IF NOT EXISTS evidence_supports ON evidence_links(task_id,criterion_ref,claim_id) WHERE assessment_row=0;
CREATE TABLE IF NOT EXISTS claim_origins(task_id TEXT,claim_id TEXT,parent_id TEXT,
 PRIMARY KEY(task_id,claim_id,parent_id));
CREATE INDEX IF NOT EXISTS claim_origin_parent ON claim_origins(task_id,parent_id,claim_id);
CREATE TABLE IF NOT EXISTS evidence_documents(task_id TEXT,artifact_id TEXT,source_id TEXT,body TEXT,
 PRIMARY KEY(task_id,artifact_id));
CREATE TABLE IF NOT EXISTS evidence_sources(task_id TEXT,source_id TEXT,body TEXT,checked INTEGER,
 PRIMARY KEY(task_id,source_id));
"""


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


class EvidenceRead:
    def __init__(self, model):
        self.model = model

    @staticmethod
    def ensure_schema(db):
        columns = {row[1] for row in db.execute("PRAGMA table_info(evidence_links)")}
        if "superseded_row" not in columns:
            db.execute("ALTER TABLE evidence_links ADD COLUMN superseded_row INTEGER")
        db.execute("CREATE INDEX IF NOT EXISTS evidence_claim_usage ON evidence_links("
                   "task_id,claim_id,candidate_ref,run_id,source_row,assessment_row,superseded_row,criterion_ref,"
                   "rule_ref,attribute_ref,relationship,via_claim_id,name)")

    @staticmethod
    def backfill_intervals(db):
        # Only the already-projected assessment pointers are needed. A later cell
        # closes the old cell's interval even if the later cell has no claim links.
        db.execute("CREATE TEMP TABLE evidence_intervals AS SELECT source_row,lead(source_row) OVER ("
                   "PARTITION BY run_id,candidate_ref,rule_ref ORDER BY source_row) AS next_row FROM assessments")
        db.execute("CREATE UNIQUE INDEX temp.evidence_interval_row ON evidence_intervals(source_row)")
        db.execute("UPDATE evidence_links SET superseded_row=(SELECT next_row FROM evidence_intervals i "
                   "WHERE i.source_row=evidence_links.assessment_row) WHERE assessment_row>0")
        db.execute("DROP TABLE temp.evidence_intervals")

    def _parents(self, db, task_id, claim_id):
        result, todo = {claim_id}, [claim_id]
        while todo:
            child = todo.pop()
            for row in db.execute("SELECT parent_id FROM claim_origins WHERE task_id=? AND claim_id=?", (task_id, child)):
                if row[0] not in result:
                    result.add(row[0])
                    todo.append(row[0])
        return result

    def _link(self, db, task_id, claim_id, criterion_ref, *, attribute_ref=None, rule_ref=None,
              candidate_ref="", run_id="", assessment_row=0, relationship="supports_criterion",
              name=None, source_row=0, verdict=None):
        if not claim_id or not criterion_ref:
            return
        for origin in self._parents(db, task_id, claim_id):
            relation = relationship if origin == claim_id else "derived_" + relationship
            db.execute("INSERT OR IGNORE INTO evidence_links(task_id,claim_id,criterion_ref,attribute_ref,rule_ref,"
                "candidate_ref,run_id,assessment_row,relationship,name,source_row,verdict,via_claim_id) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (task_id, origin, criterion_ref, attribute_ref, rule_ref, candidate_ref or "", run_id or "",
                 assessment_row, relation, name, source_row, verdict, claim_id))

    def criterion(self, db, task_id, ref, kind, record, source_row):
        attribute = record.get("attribute") or record
        rule = record.get("rule") or {}
        attribute_ref = ref if kind == "attribute" else record.get("attribute_ref")
        rule_ref = ref if kind == "rule" else None
        if kind == "rule":
            row = db.execute("SELECT body FROM criterion_versions WHERE task_id=? AND ref=?", (task_id, attribute_ref)).fetchone()
            attribute = json.loads(row[0]) if row else {}
            db.execute("DELETE FROM evidence_links WHERE task_id=? AND criterion_ref=? AND assessment_row=0", (task_id, attribute_ref))
        refs = list(dict.fromkeys((record.get("supporting_claim_ids") or record.get("supporting_claim_refs") or [])
                                 + (attribute.get("supporting_claim_refs") or [])))
        for claim in refs:
            self._link(db, task_id, claim, ref, attribute_ref=attribute_ref, rule_ref=rule_ref,
                       name=attribute.get("name"), source_row=source_row)

    def claim(self, db, source, task_id, pointer):
        raw = self.model._artifact(source, pointer["artifact_id"], {"claim"})
        compact = self.model._claim(source, dict(pointer, body=None), claim=raw)
        compact.update(context=claim_context(raw), summary=fact_summary(raw),
                       value_low=raw.get("value_low"), value_high=raw.get("value_high"),
                       document_artifact_id=raw.get("document_artifact_id"),
                       claim_artifact_id=pointer["artifact_id"], location=raw.get("location") or {},
                       projection_version=1)
        parent = raw.get("reuse_of_claim_id")
        derived = raw.get("derived_from")
        parents = [parent] if parent else []
        if isinstance(derived, dict) and derived.get("claim_id"):
            parents.append(derived["claim_id"])
        for parent in parents:
            if parent != pointer["claim_id"]:
                db.execute("INSERT OR IGNORE INTO claim_origins VALUES (?,?,?)", (task_id, pointer["claim_id"], parent))
        document_id = raw.get("document_artifact_id")
        document_meta = None
        if document_id:
            row = db.execute("SELECT body FROM evidence_documents WHERE task_id=? AND artifact_id=?", (task_id, document_id)).fetchone()
            if row:
                document_meta = json.loads(row[0])
            else:
                document = self.model._artifact(source, document_id, {"document"})
                if document.get("source_id") == compact.get("source_id"):
                    document_meta = {key:document.get(key) for key in ("title", "year", "identifiers", "source_id", "reading_depth", "access_state", "license")}
                    document_meta["url"] = (document.get("source_hit") or {}).get("url")
                else:
                    document_meta = {}
                db.execute("INSERT OR REPLACE INTO evidence_documents VALUES (?,?,?,?)",
                           (task_id, document_id, compact.get("source_id"), encoded(document_meta)))
        compact["title"] = (document_meta or {}).get("title") or compact.get("title")
        digest = source.execute("SELECT sha256 FROM artifacts WHERE artifact_id=? AND kind='document'", (document_id,)).fetchone() if document_id else None
        compact["source_fact_hash"] = hashlib.sha256(encoded([raw, digest[0] if digest else None]).encode()).hexdigest()
        source_meta = db.execute("SELECT body FROM evidence_sources WHERE task_id=? AND source_id=?",(task_id,compact.get("source_id"))).fetchone()
        source_hash = (json.loads(source_meta[0]) if source_meta else {}).get("source_record_hash")
        compact["source_context_hash"] = hashlib.sha256(encoded([compact["source_fact_hash"],source_hash]).encode()).hexdigest()
        if compact.get("source_id"):
            db.execute("INSERT OR IGNORE INTO evidence_sources VALUES (?,?,?,0)", (task_id, compact["source_id"], "{}"))
        return compact

    def assessment(self, db, source, task_id, pointer):
        previous = db.execute("SELECT max(source_row) FROM assessments WHERE run_id=? AND candidate_ref=? "
                              "AND rule_ref=? AND source_row<?", (pointer["run_id"],pointer["candidate_ref"],
                              pointer["rule_ref"],pointer["source_row"])).fetchone()[0]
        if previous is not None:
            db.execute("UPDATE evidence_links SET superseded_row=? WHERE assessment_row=? AND assessment_row>0",
                       (pointer["source_row"],previous))
        cell = self.model._artifact(source, pointer["artifact_id"], {"assessment"})
        attribute = db.execute("SELECT body FROM criterion_versions WHERE task_id=? AND ref=?", (task_id, pointer["attribute_ref"])).fetchone()
        name = (json.loads(attribute[0]) if attribute else {}).get("name")
        common = dict(attribute_ref=pointer["attribute_ref"], rule_ref=pointer["rule_ref"],
                      candidate_ref=pointer["candidate_ref"], run_id=pointer["run_id"],
                      assessment_row=pointer["source_row"], source_row=pointer["source_row"], name=name, verdict=cell.get("verdict"))
        for relationship, refs in (("used_in_assessment",cell.get("value_source_claim_refs") or []),
                                   ("counter_evidence",cell.get("conflicting_claim_refs") or []),
                                   ("set_aside",[v.get("claim_id") for v in cell.get("set_aside_claims") or []])):
            for claim in refs:
                if claim:
                    self._link(db, task_id, claim, pointer["rule_ref"], relationship=relationship, **common)
        # A basis for a criterion is not a candidate-specific measurement. Keep
        # that relation explicit, including where the resulting cell was unknown.
        supports = db.execute("SELECT claim_id FROM evidence_links WHERE task_id=? AND criterion_ref=? "
                              "AND assessment_row=0", (task_id, pointer["rule_ref"])).fetchall()
        for row in supports:
            self._link(db, task_id, row[0], pointer["rule_ref"], relationship="criterion_basis", **common)

    def backfill(self, db, source):
        for pointer in db.execute("SELECT * FROM claims ORDER BY source_row").fetchall():
            compact = self.claim(db, source, pointer["task_id"], dict(pointer))
            searchable=" ".join(str(compact.get(key) or "") for key in ("claim_id","source_id","candidate_ref","attribute_ref","title","quote","statement","basis"))
            db.execute("UPDATE claims SET body=?,search_text=? WHERE source_row=?", (encoded(compact),searchable,pointer["source_row"]))
        for row in db.execute("SELECT * FROM criterion_versions ORDER BY source_row").fetchall():
            self.criterion(db,row["task_id"],row["ref"],row["kind"],json.loads(row["body"]),row["source_row"])
        seen = set()
        for row in db.execute("SELECT * FROM criterion_changes ORDER BY source_row").fetchall():
            change = json.loads(row["body"])
            artifact = change.get("artifact_id")
            if change.get("kind") in ("attribute", "rule"):
                continue
            ref = f"{row['criterion_id']}@v{row['version']}"
            if (row["task_id"],ref) in seen:
                continue
            item = self.model._artifact(source,artifact,{"criterion_candidate"})
            if not item and change.get("sources"):
                item={"attribute":{"name":(change.get("after") or {}).get("name")},"supporting_claim_ids":change["sources"]}
            if item:
                self.criterion(db,row["task_id"],ref,"pool",item,row["source_row"])
                seen.add((row["task_id"],ref))
        for row in db.execute("SELECT a.*,r.task_id FROM assessments a JOIN runs r ON r.run_id=a.run_id ORDER BY a.source_row").fetchall():
            self.assessment(db,source,row["task_id"],row)

    def hydrate_sources(self, db, source):
        pending = db.execute("SELECT task_id,source_id FROM evidence_sources WHERE checked=0").fetchall()
        if not pending:
            return
        wanted = list({row["source_id"] for row in pending})
        found = {}
        for offset in range(0,len(wanted),400):
            ids = wanted[offset:offset+400]
            rows = source.execute("SELECT artifact_id FROM artifacts WHERE kind='source' "
                "AND json_extract(body,'$.payload.source_id') IN ("+','.join('?' for _ in ids)+") ORDER BY created_at",ids)
            for row in rows:
                raw = self.model._artifact(source,row[0],{"source"})
                if raw.get("source_id"):
                    found[raw["source_id"]] = {key:raw.get(key) for key in ("source_id","title","url","identifiers","source_status","year")}
                    found[raw["source_id"]]["source_record_hash"] = hashlib.sha256(encoded(raw).encode()).hexdigest()
        for row in pending:
            db.execute("UPDATE evidence_sources SET body=?,checked=1 WHERE task_id=? AND source_id=?",
                       (encoded(found.get(row["source_id"],{})),row["task_id"],row["source_id"]))
            meta=found.get(row["source_id"],{})
            for claim in db.execute("SELECT source_row,body,search_text FROM claims WHERE task_id=? AND source_id=?",(row["task_id"],row["source_id"])).fetchall():
                body=json.loads(claim["body"])
                body["title"] = body.get("title") or meta.get("title")
                body["source_context_hash"] = hashlib.sha256(encoded([body.get("source_fact_hash"),meta.get("source_record_hash")]).encode()).hexdigest()
                db.execute("UPDATE claims SET body=?,search_text=? WHERE source_row=?",(encoded(body),(claim["search_text"] or "")+" "+(body.get("title") or ""),claim["source_row"]))

    def source_view(self, db, task_id, claim, *, source=None, detail=False):
        source_id, document_id = claim.get("source_id"), claim.get("document_artifact_id")
        row = db.execute("SELECT body FROM evidence_sources WHERE task_id=? AND source_id=?", (task_id,source_id)).fetchone()
        metadata = json.loads(row[0]) if row else {}
        doc = db.execute("SELECT body FROM evidence_documents WHERE task_id=? AND artifact_id=?", (task_id,document_id)).fetchone() if document_id else None
        pinned = json.loads(doc[0]) if doc else {}
        value = {"source_id":source_id,"title":pinned.get("title") or claim.get("title") or metadata.get("title"),
                 "url":claim.get("url") or pinned.get("url") or metadata.get("url"),
                 "locator":claim.get("locator"),"excerpt":claim.get("quote"),
                 "section_path":(claim.get("location") or {}).get("section_path") or [],
                 "document_artifact_id":document_id,"context_available":False,"context_status":"detail_not_loaded"}
        if detail:
            document = self.model._artifact(source,document_id,{"document"}) if document_id and source is not None else {}
            if document.get("source_id") != source_id:
                document = {}
            value.update(original_context(document,claim.get("location") or {}))
        return value

    @staticmethod
    def _scope(snapshot):
        if not snapshot:
            return "", []
        return (" AND u.source_row<=? AND (u.assessment_row=0 OR (u.run_id=? AND "
                "(u.superseded_row IS NULL OR u.superseded_row>?)))",
                [snapshot["published_row"],snapshot["run_id"],snapshot["published_row"]])

    def links(self, db, task_id, claim_id, *, snapshot=None, candidate_ref=None, criteria_page=1, candidate_page=1, page_size=3):
        mode = "selected_snapshot" if snapshot is not None else "latest_snapshot"
        if snapshot is None:
            snapshot = self.model._snapshot_row(db, task_id, None)
        if snapshot is None:
            mode = "task_history"
        scope, params = self._scope(snapshot)
        where = "u.task_id=? AND u.claim_id=?" + scope
        values = [task_id,claim_id,*params]
        if candidate_ref:
            where += " AND u.candidate_ref IN ('',?)"
            values.append(candidate_ref)
        criteria_total = db.execute("SELECT count(DISTINCT u.criterion_ref) FROM evidence_links u INDEXED BY evidence_claim_usage WHERE " + where,values).fetchone()[0]
        criteria = [dict(row) for row in db.execute("SELECT u.criterion_ref AS detail_ref,max(u.name) AS name," 
            "u.attribute_ref,u.rule_ref,group_concat(DISTINCT u.relationship) AS relationships,group_concat(DISTINCT u.via_claim_id) AS via_claim_refs FROM evidence_links u INDEXED BY evidence_claim_usage WHERE " + where +
            " GROUP BY u.criterion_ref ORDER BY (u.rule_ref IS NULL),max(u.source_row) DESC,u.criterion_ref LIMIT ? OFFSET ?",
            (*values,page_size,(criteria_page-1)*page_size))]
        for item in criteria:
            item["via_claim_refs"] = item["via_claim_refs"].split(",")
            item["relationships"] = item["relationships"].split(",")
            item["relationship"] = item["relationships"][0] if len(item["relationships"])==1 else "multiple_recorded_uses"
        candidate_where = where + " AND u.candidate_ref!=''"
        candidate_total = db.execute("SELECT count(*) FROM (SELECT u.candidate_ref,u.run_id FROM evidence_links u INDEXED BY evidence_claim_usage WHERE " +
            candidate_where+" GROUP BY u.candidate_ref,u.run_id)",values).fetchone()[0]
        candidates = []
        for row in db.execute("SELECT u.candidate_ref,u.run_id,group_concat(DISTINCT u.relationship) AS relationships,group_concat(DISTINCT u.via_claim_id) AS via_claim_refs "
                              "FROM evidence_links u INDEXED BY evidence_claim_usage WHERE "+candidate_where+" GROUP BY u.candidate_ref,u.run_id "
                              "ORDER BY max(u.source_row) DESC,u.candidate_ref LIMIT ? OFFSET ?",
                              (*values,page_size,(candidate_page-1)*page_size)):
            item = dict(row)
            item["via_claim_refs"] = item["via_claim_refs"].split(",")
            item["relationships"] = item["relationships"].split(",")
            item["relationship"] = item["relationships"][0] if len(item["relationships"])==1 else "multiple_recorded_uses"
            snap = snapshot if snapshot and snapshot["run_id"]==row["run_id"] else db.execute("SELECT * FROM snapshots WHERE task_id=? AND run_id=? ORDER BY published_row DESC LIMIT 1",(task_id,row["run_id"])).fetchone()
            item["snapshot_id"] = snap["snapshot_id"] if snap else None
            label = db.execute("SELECT label FROM candidate_rows WHERE snapshot_id=? AND candidate_ref=?",(item["snapshot_id"],row["candidate_ref"])).fetchone() if snap else None
            if not label:
                label = db.execute("SELECT c.label FROM candidate_rows c JOIN snapshots s ON s.snapshot_id=c.snapshot_id "
                                   "WHERE s.task_id=? AND c.candidate_ref=? ORDER BY s.published_row DESC LIMIT 1",(task_id,row["candidate_ref"])).fetchone()
            item["label"] = label[0] if label else row["candidate_ref"]
            candidates.append(item)
        candidate_unit = "unique_candidates" if snapshot else "candidate_run_records"
        def page(items,total,number,unit):
            return {"items":items,"total":total,"page":number,"page_size":page_size,"has_more":number*page_size<total,"unit":unit}
        return {"criteria":page(criteria,criteria_total,criteria_page,"criterion_versions"),
                "candidates":page(candidates,candidate_total,candidate_page,candidate_unit),
                "scope":{"candidate_ref":candidate_ref,"snapshot_id":snapshot["snapshot_id"] if snapshot else None,
                         "snapshot_published_at":snapshot["published_at"] if snapshot else None,
                         "mode":mode,"candidate_unit":candidate_unit,
                         "criteria_unit":"criterion_versions"}}

    def enrich(self, db, source, task_id, claim, *, snapshot=None, candidate_ref=None, detail=False, criteria_page=1, candidate_page=1, page_size=3):
        result = dict(claim)
        result["source"] = self.source_view(db,task_id,claim,source=source,detail=detail)
        result["title"] = result["source"]["title"]
        usages = self.links(db,task_id,claim["claim_id"],snapshot=snapshot,candidate_ref=candidate_ref,criteria_page=criteria_page,candidate_page=candidate_page,page_size=page_size)
        result["links"] = {"criteria":usages["criteria"]["items"],"candidates":usages["candidates"]["items"],
                           "counts":{key:usages[key]["total"] for key in ("criteria","candidates")},"scope":usages["scope"]}
        result["summary"] = claim.get("summary") or {"text":claim.get("statement"),"method":"recorded_fact_projection","derived":True,"claim_refs":[claim["claim_id"]]}
        if detail:
            result.update(criteria_usage=usages["criteria"],candidate_usage=usages["candidates"])
            names = [item.get("name") or item["detail_ref"] for item in usages["criteria"]["items"][:3]]
            text = ("Linked to " + str(usages["criteria"]["total"]) + " recorded criterion versions: " + "; ".join(names) + ".") if names else "No recorded use by a criterion was found in this task."
            unit = "unique candidates in this snapshot" if usages["scope"]["snapshot_id"] else "candidate/run records across task history"
            text += f" Linked {unit}: {usages['candidates']['total']}. Criterion-basis links explain the rule's rationale; they are not candidate-specific observations."
            result["research_relevance"] = {"text":text,"method":"recorded_usage_projection","derived":True,
                                            "claim_refs":[claim["claim_id"]],"scope_note":(claim.get("context") or {}).get("population")}
        return result
