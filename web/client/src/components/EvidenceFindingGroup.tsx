import type { Evidence } from '../api/types';
import { useI18n } from '../i18n';
import { EvidenceCard } from './EvidenceCard';
import type { ResearchNavigate } from './ResearchLinks';

export function groupSavedFindings(records: Evidence[]): Evidence[][] {
  const groups = new Map<string, Evidence[]>();
  records.forEach((record, index) => {
    const key = record.finding_identity ? `${record.source_id}/${record.finding_identity}` : `uncompared/${index}`;
    const group = groups.get(key) || []; group.push(record); groups.set(key, group);
  });
  function used(record: Evidence) {
    return [...record.links?.criteria || [], ...record.links?.candidates || []].some(link =>
      (link.relationships || (link.relationship ? [link.relationship] : [])).some(role => role === 'used_in_assessment' || role === 'derived_used_in_assessment'));
  }
  return [...groups.values()].map(group => [...group].sort((left, right) => Number(used(right)) - Number(used(left))));
}

export function EvidenceFindingGroup({ records, task, snapshot, onOpen, onNavigate }: {
  records: Evidence[]; task: string; snapshot?: string; onOpen: (claim: string) => void; onNavigate: ResearchNavigate;
}) {
  const { t } = useI18n();
  return <div className="saved-finding-group"><EvidenceCard record={records[0]} task={task} snapshot={snapshot} onOpen={onOpen} onNavigate={onNavigate} compactSource />
    {records.length > 1 && <details className="saved-finding-records"><summary>{records.length} {t('saved records of this finding · see records', '条相同发现的保存记录 · 查看记录')}</summary><p>{t('Exact saved scientific fields match on this page. Each record retains its own usage and provenance.', '本页这些记录的完整科学字段一致，各记录的采用关系与来源留痕分别保留。')}</p>{records.slice(1).map((record, index) => <EvidenceCard key={`${record.claim_id}/${index}`} record={record} task={task} snapshot={snapshot} onOpen={onOpen} onNavigate={onNavigate} compactSource />)}</details>}
  </div>;
}
