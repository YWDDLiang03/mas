"""Preview, map and commit user CSV data as immutable local datasets.

Import preserves declared observations and provenance. It does not establish
peer review, candidate suitability, a threshold or permission to run a tool.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import re
import threading
from pathlib import Path
from typing import Any

from mas.core.canonical import sha256_hex
from mas.core.clock import utc_now

MAX_BYTES = 8 * 1024 * 1024
MAX_ROWS = 50000
ENTITY_TYPES = ('drug', 'carrier', 'general')
BASES = ('measured', 'curated', 'predicted', 'simulated', 'derived')
FIELDS = {
    'candidates': [
        ('candidate_id', 'Candidate ID', True), ('name', 'Name', False),
        ('smiles', 'SMILES', False), ('inchikey', 'InChIKey', False),
        ('chembl_id', 'ChEMBL ID', False), ('description', 'Description', False)],
    'measurements': [
        ('candidate_id', 'Candidate ID', True), ('property', 'Property', True),
        ('value', 'Value', True), ('unit', 'Unit', False), ('basis', 'Evidence basis', True),
        ('conditions', 'Experimental conditions', False), ('source', 'Source', False),
        ('summary', 'Observation summary', False)],
}
ALIASES = {
    'candidate_id': ('candidate_id', 'id', 'sample_id', '候选编号', '样品编号'),
    'name': ('name', 'label', 'candidate_name', 'sample_name', '名称', '候选名称'),
    'property': ('property', 'property_id', 'measurement', 'endpoint', '指标', '性质'),
    'value': ('value', 'result', '数值', '结果'), 'unit': ('unit', 'units', '单位'),
    'basis': ('basis', 'determination_basis', 'evidence_basis', '依据'),
    'conditions': ('conditions', 'condition', '实验条件'),
    'source': ('source', 'source_id', 'doi', '来源'),
    'summary': ('summary', 'observation', 'conclusion', '观察结论'),
}


def template(kind: str) -> str:
    """Examples are visibly synthetic, with stable IDs linking the two files."""
    if kind not in FIELDS:
        raise ValueError('Choose candidates or measurements.')
    output = io.StringIO(newline='')
    writer = csv.writer(output)
    writer.writerow([field[0] for field in FIELDS[kind]])
    if kind == 'candidates':
        writer.writerows([
            ['EXAMPLE-A', 'Example carrier A', '', '', '', 'Synthetic example; replace with your candidates'],
            ['EXAMPLE-B', 'Example carrier B', '', '', '', 'Synthetic example; replace with your candidates']])
    else:
        writer.writerows([
            ['EXAMPLE-A', 'particle_size', '120', 'nm', 'measured',
             'DLS; aqueous dispersion; 25 C', 'Synthetic example', 'Example observation, not a research result'],
            ['EXAMPLE-B', 'particle_size', '170', 'nm', 'measured',
             'DLS; aqueous dispersion; 25 C', 'Synthetic example', 'Example observation, not a research result'],
            ['EXAMPLE-A', 'cell_viability', '92', '%', 'measured',
             '24 h; dose 10 ug/mL; model specified by the researcher', 'Synthetic example', 'Example observation'],
            ['EXAMPLE-B', 'cell_viability', '85', '%', 'measured',
             '24 h; dose 10 ug/mL; model specified by the researcher', 'Synthetic example', 'Example observation']])
    return output.getvalue()


class UploadStore:
    def __init__(self, store_root: str | Path):
        self.parent = Path(store_root).resolve().parent
        self.root = self.parent / 'workbench-uploads'
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    def _path(self, identity: str, suffix: str) -> Path:
        if not re.fullmatch(r'(?:preview|upl)_[0-9a-f]{64}', str(identity)):
            raise ValueError('Choose a saved upload from this workspace.')
        return self.root / f'{identity}{suffix}'

    def _immutable(self, path: Path, body: dict) -> None:
        # Every identity is content-addressed. A repeated commit returns its original record.
        with self._lock:
            if not path.exists():
                temporary = path.with_suffix(path.suffix + '.tmp')
                temporary.write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding='utf-8')
                temporary.replace(path)

    def read(self, identity: str) -> dict:
        path = self._path(identity, '.json')
        if not path.is_file():
            raise ValueError('This upload is no longer available. Select the file again.')
        record = json.loads(path.read_text(encoding='utf-8'))
        if identity.startswith('preview_'):
            digest = hashlib.sha256(record['content'].encode('utf-8')).hexdigest()
            expected = 'preview_' + sha256_hex({'content': digest, 'kind': record['kind'], 'filename': record['filename']})
            valid = expected == identity and digest == record['content_sha256']
        else:
            signature = {key: record[key] for key in ('kind', 'mapping', 'entity_type', 'library_id',
                'content_sha256', 'filename', 'canonical')}
            valid = 'upl_' + sha256_hex(signature) == identity
            valid = valid and record['candidates' if record['kind'] == 'candidates' else 'measurements'] == record['canonical']
        if not valid:
            raise ValueError('This saved dataset changed outside the importer. Import the revised CSV as a new version.')
        return record

    def list_libraries(self) -> list[dict]:
        rows = []
        for path in sorted(self.root.glob('upl_*.meta.json')):
            item = json.loads(path.read_text(encoding='utf-8'))
            if item.get('kind') == 'candidates':
                rows.append({'id': 'upload:' + item['upload_id'], 'label': item['label'],
                    'count': item['row_count'], 'path': str(self._path(item['upload_id'], '.json')), 'source': item['source_id'],
                    'as_of': item['created_at'], 'entity_type': item['entity_type'], 'uploaded': True,
                    'content_sha256': item['content_sha256']})
        return rows

    def library(self, identity: str) -> dict:
        if str(identity).startswith('upload:'):
            saved = self.read(identity.removeprefix('upload:'))
            if saved.get('kind') != 'candidates':
                raise ValueError('Select a candidate dataset for these measurements.')
            return saved
        if not re.fullmatch(r'universe[^/\\]*\.json', str(identity)):
            raise ValueError('Select a candidate library before importing measurements.')
        path = self.parent / identity
        if not path.is_file():
            raise ValueError('The selected candidate library is unavailable.')
        saved = json.loads(path.read_text(encoding='utf-8'))
        return dict(saved, candidates=[{'candidate_id': row.get('candidate_id') or row.get('inchikey'),
            'label': row.get('label') or row.get('name'), 'entity_kind': 'drug',
            'identifiers': [{'scheme': key, 'value': row[key]} for key in ('inchikey', 'smiles', 'chembl_id') if row.get(key)],
            'metadata': {'source': saved.get('source')}} for row in saved['universe']])

    @staticmethod
    def _parse(content: str) -> tuple[list[str], list[tuple[int, dict[str, str]]]]:
        if not isinstance(content, str) or not content.strip():
            raise ValueError('Choose a non-empty UTF-8 CSV file.')
        if len(content.encode('utf-8')) > MAX_BYTES:
            raise ValueError('The CSV limit is 8 MB. Split larger datasets before importing.')
        if '\x00' in content or '\ufffd' in content:
            raise ValueError('Save this file as UTF-8 CSV before importing it.')
        reader = csv.reader(io.StringIO(content.lstrip('\ufeff'), newline=''), strict=True)
        try:
            headers = [h.strip() for h in next(reader)]
            if not headers or len(headers) > 64 or any(not h for h in headers) or len(set(headers)) != len(headers):
                raise ValueError('Use 1–64 distinct, non-empty column headers.')
            rows = []
            for row in reader:
                if not any(value.strip() for value in row):
                    continue
                if len(row) != len(headers):
                    raise ValueError(f'CSV line {reader.line_num} has {len(row)} fields; expected {len(headers)}.')
                rows.append((reader.line_num, dict(zip(headers, row))))
                if len(rows) > MAX_ROWS:
                    raise ValueError('Import at most 50,000 data rows per file.')
        except (csv.Error, StopIteration) as error:
            raise ValueError(f'The CSV could not be read: {error}') from error
        if not rows:
            raise ValueError('Add at least one data row below the column headers.')
        return headers, rows

    @staticmethod
    def _mapping(kind: str, headers: list[str], supplied: dict | None) -> dict:
        if supplied is not None and not isinstance(supplied, dict):
            raise ValueError('Map each field to a CSV column.')
        allowed = {f[0] for f in FIELDS[kind]}
        if supplied and set(supplied) - allowed:
            raise ValueError('The mapping contains an unknown field.')
        lower = {h.lower(): h for h in headers}
        mapping = {}
        for key in allowed:
            if supplied is not None and key in supplied:
                column = supplied[key]
                if column and column not in headers:
                    raise ValueError(f'The mapped column for {key} is absent from this file.')
                mapping[key] = column or None
            else:
                mapping[key] = next((lower[a.lower()] for a in ALIASES.get(key, (key,)) if a.lower() in lower), None)
        mapped = [value for value in mapping.values() if value]
        if len(set(mapped)) != len(mapped):
            raise ValueError('Map each CSV column to at most one field.')
        return mapping

    def preview(self, request: dict) -> dict:
        if request.get('upload_id'):
            raw = self.read(request['upload_id'])
            if not raw['upload_id'].startswith('preview_'):
                raise ValueError('Use the original preview to change column mapping.')
        else:
            kind = request.get('kind')
            if kind not in FIELDS:
                raise ValueError('Choose a candidate list or a measurement table.')
            content = request.get('content')
            self._parse(content)
            name = Path(str(request.get('filename') or 'upload.csv')).name[:160]
            digest = hashlib.sha256(content.encode('utf-8')).hexdigest()
            identity = 'preview_' + sha256_hex({'content': digest, 'kind': kind, 'filename': name})
            raw = {'upload_id': identity, 'kind': kind, 'filename': name, 'content': content,
                   'content_sha256': digest, 'created_at': utc_now()}
            self._immutable(self._path(identity, '.json'), raw)
        entity_type = request.get('entity_type', 'general')
        if entity_type not in ENTITY_TYPES:
            raise ValueError('Choose drug, carrier or general candidates.')
        kind = raw['kind']
        headers, raw_rows = self._parse(raw['content'])
        mapping = self._mapping(kind, headers, request.get('mapping'))
        errors, warnings, values, seen = [], [], [], set()
        for key, label, required in FIELDS[kind]:
            if required and not mapping.get(key):
                errors.append({'field': key, 'message': f'Map the {label} field to a column.'})
        library_id = request.get('library_id')
        candidate_ids = None
        if kind == 'measurements':
            if library_id:
                candidate_ids = {row['candidate_id'] for row in self.library(library_id)['candidates']}
            else:
                errors.append({'field': 'library_id', 'message': 'Select the candidate library these measurements describe.'})
        valid_rows = 0
        canonical = []
        for row_number, cells in raw_rows:
            row = {key: cells.get(column, '').strip() if column else '' for key, column in mapping.items()}
            problems = []
            def bad(field, message):
                problems.append({'row': row_number, 'field': field, 'message': message})
            for key, _, required in FIELDS[kind]:
                if required and not row[key]:
                    bad(key, 'This field is required.')
            cid = row['candidate_id']
            if len(cid) > 200:
                bad('candidate_id', 'Use a candidate ID of at most 200 characters.')
            if kind == 'candidates':
                if cid in seen:
                    bad('candidate_id', 'Candidate IDs must be unique. Measurements belong in the separate table.')
                seen.add(cid)
                item = {'candidate_id': cid, 'label': row['name'] or cid, 'entity_kind': entity_type,
                    'identifiers': [{'scheme': key, 'value': row[key]} for key in ('smiles', 'inchikey', 'chembl_id') if row[key]],
                    'metadata': {key: value for key, value in cells.items() if key not in set(mapping.values())},
                    'description': row['description']}
            else:
                if candidate_ids is not None and cid not in candidate_ids:
                    bad('candidate_id', 'This ID is absent from the selected candidate library; names are not matched automatically.')
                if row['basis'] not in BASES:
                    bad('basis', 'Choose measured, curated, predicted, simulated or derived; evidence basis is not guessed.')
                val: Any = row['value']
                if val.lower() in ('true', 'false'):
                    val = val.lower() == 'true'
                else:
                    try:
                        val = float(val)
                        if not math.isfinite(val):
                            bad('value', 'Use a finite number, true/false, or a recorded category; leave missing observations out.')
                        if not row['unit']:
                            bad('unit', 'A numeric observation needs a unit; use 1 for a dimensionless quantity.')
                    except ValueError:
                        if val.lower() in ('na', 'n/a', 'nan', 'none', 'null', 'unknown', 'missing'):
                            bad('value', 'Missing observations should be omitted, not represented as a measured category.')
                conditions = {}
                if row['conditions']:
                    if row['conditions'].startswith('{'):
                        try:
                            conditions = json.loads(row['conditions'])
                            if not isinstance(conditions, dict):
                                raise ValueError('not an object')
                            json.dumps(conditions, allow_nan=False)
                        except ValueError:
                            bad('conditions', 'Use a valid JSON object or plain text describing the conditions.')
                    else:
                        conditions = {'description': row['conditions']}
                item = {'measurement_id': 'measurement_' + sha256_hex({'upload': raw['content_sha256'], 'mapping': mapping, 'row': row_number})[:24],
                    'candidate_id': cid, 'property_id': row['property'], 'property_label': row['property'],
                    'value': val, 'unit': row['unit'] or None, 'conditions': conditions,
                    'source_id': 'src_upload_' + raw['content_sha256'],
                    'source_locator': f'CSV row {row_number}', 'declared_source': row['source'] or raw['filename'],
                    'basis': row['basis'], 'normalized_statement': row['summary'] or
                        f"{cid}: {row['property']} = {row['value']} {row['unit']}.".strip(),
                    'row_number': row_number,
                    'provenance': {'filename': raw['filename'], 'content_sha256': raw['content_sha256'],
                                   'declared_source': row['source'] or None, 'scientific_review': 'not_performed'}}
            errors.extend(problems)
            if not problems:
                valid_rows += 1
                canonical.append(item)
            if len(values) < 10:
                values.append({'row_number': row_number, 'values': row, 'errors': problems})
        if kind == 'measurements':
            warnings.append('Imported rows keep their declared evidence basis. Import checks structure and identity; research review remains separate.')
            if any(not row['conditions'] for row in canonical):
                warnings.append('Some observations have no recorded experimental conditions. Their scope will remain unspecified.')
        else:
            warnings.append('Candidate metadata alone is not measurement evidence. Add a measurement table or choose an evidence collection.')
        return {'upload_id': raw['upload_id'], 'kind': kind, 'filename': raw['filename'], 'headers': headers,
            'field_schema': [{'key': key, 'label': label, 'required': required, 'type': 'text',
                             **({'choices': list(BASES)} if key == 'basis' else {})} for key, label, required in FIELDS[kind]],
            'mapping': mapping, 'preview_rows': values, 'row_count': len(raw_rows), 'valid_rows': valid_rows,
            'errors': errors[:200], 'error_count': len(errors), 'warnings': warnings,
            'can_commit': not errors, 'entity_type': entity_type, 'library_id': library_id,
            '_canonical': canonical, '_raw': raw}

    def commit(self, identity: str, request: dict) -> dict:
        result = self.preview(dict(request, upload_id=identity))
        if not result['can_commit']:
            raise ValueError('Resolve the row and column issues in the preview before importing.')
        raw, canonical = result['_raw'], result['_canonical']
        signature = {key: result[key] for key in ('kind', 'mapping', 'entity_type', 'library_id')}
        signature.update(content_sha256=raw['content_sha256'], filename=raw['filename'], canonical=canonical)
        committed_id = 'upl_' + sha256_hex(signature)
        kind = result['kind']
        record = dict(signature, upload_id=committed_id, row_count=len(canonical), created_at=utc_now(),
            label=f"{raw['filename']} · {len(canonical):,} {'candidates' if kind == 'candidates' else 'observations'}",
            source_id='src_upload_' + raw['content_sha256'], original_upload_id=raw['upload_id'])
        record['candidates' if kind == 'candidates' else 'measurements'] = canonical
        if kind == 'candidates':
            record.update(universe=canonical, source=record['source_id'], retrieved_at=record['created_at'])
        self._immutable(self._path(committed_id, '.json'), record)
        record = self.read(committed_id)
        self._immutable(self._path(committed_id, '.meta.json'), {key: record[key] for key in
            ('upload_id', 'kind', 'row_count', 'created_at', 'label', 'source_id', 'entity_type', 'content_sha256')})
        return {'upload_id': committed_id, 'kind': kind, 'row_count': record['row_count'], 'label': record['label'],
            'library_id': 'upload:' + committed_id if kind == 'candidates' else result['library_id'],
            'evidence_upload_id': committed_id if kind == 'measurements' else None,
            'entity_type': record['entity_type'], 'content_sha256': raw['content_sha256']}

    @staticmethod
    def public_preview(value: dict) -> dict:
        return {key: item for key, item in value.items() if not key.startswith('_')}
