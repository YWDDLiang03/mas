import { useEffect, useId, useState } from 'react';
import { api } from '../api/client';
import type { Workflow } from '../api/types';
import { phaseText, stateText, useI18n } from '../i18n';
import { Audit, Badge, Icon, valueText } from './UI';
import { WorkflowStages } from './WorkflowStages';

function elapsed(start: string, end: string | null | undefined, now: number) {
  const seconds = Math.max(0, Math.floor(((end ? Date.parse(end) : now) - Date.parse(start)) / 1000));
  if (!Number.isFinite(seconds)) return '—';
  return seconds < 60 ? `${seconds}s` : seconds < 3600 ? `${Math.floor(seconds / 60)}m ${seconds % 60}s` : `${Math.floor(seconds / 3600)}h ${Math.floor(seconds % 3600 / 60)}m`;
}
export function progressMessage(workflow: Pick<Workflow, 'message' | 'phase'> & Partial<Pick<Workflow, 'state' | 'error' | 'activity_detail'>>, t: (en: string, zh: string) => string) {
  const message = workflow.message || '';
  const poolStages: Record<string, string> = { 'distill pool': 'distill', 'refine pool': 'refine', 'filter pool': 'filter', 'critique pool': 'review', 'critic pool': 'review', 'adjudicate merges': 'merge' };
  const genericReview = ['Reviewing and consolidating the current criteria', 'Checking source support and applicability'].includes(message.trim());
  if (workflow.state === 'running' && !workflow.error && genericReview && workflow.phase === 'refine') {
    const detail = workflow.activity_detail?.trim() || '';
    const batch = /^(.*?)\s+\(batch ([1-9]\d*)\/([1-9]\d*)\)$/.exec(detail);
    if (batch && poolStages[batch[1]] && Number(batch[2]) <= Number(batch[3])) return phaseText(poolStages[batch[1]], t) + t(` · batch ${batch[2]} of ${batch[3]}`, ` · 批次 ${batch[2]} / ${batch[3]}`);
    if (poolStages[detail]) return phaseText(poolStages[detail], t);
  }
  const systemMessages: Record<string, [string, string]> = {
    'Paused at a saved work boundary': ['Paused at a saved work boundary', '工作已保存，研究已暂停。'],
    'Pausing after the current activity': ['Pausing after the current activity', '当前活动结束后暂停。'],
    'Stopping after the current activity': ['Stopping after the current activity', '当前活动结束后停止。'],
    'Waiting to start': ['Waiting to start', '等待开始。'],
    'Stopped': ['Stopped', '已停止。'],
    'Continuing from the saved checkpoint': ['Continuing from the saved checkpoint', '从已保存的位置继续。'],
    'Preparing a new evaluation from the saved criteria and evidence': ['Preparing a new evaluation from the saved criteria and evidence', '正在使用已保存的标准和证据准备新评估。'],
    'Continuing the investigation': ['Continuing the investigation', '正在继续研究。'],
    'Saved for continuation': ['Saved for continuation', '工作已保存，可稍后继续。'],
    'The investigation needs attention': ['The investigation needs attention', '研究需要处理。'],
    'Workbench restarted. Continue from the saved checkpoint.': ['Workbench restarted. Continue from the saved checkpoint.', '工作台已重启，可从已保存的位置继续。'],
    'Developing criteria from the selected evidence': ['Developing criteria from the selected evidence', '正在根据所选证据生成标准。'],
    'Reviewing and consolidating the current criteria': ['Reviewing and consolidating the current criteria', '正在复核并整合当前标准。'],
    'Checking source support and applicability': ['Checking source support and applicability', '正在核查来源依据与适用性。'],
    'Re-evaluating the affected criteria with the new version': ['Re-evaluating the affected criteria with the new version', '正在使用新版本重新评估受影响的标准。'],
  };
  const evidenceDimension = /^Developing criteria from saved evidence · (.+)$/.exec(message.trim());
  if (evidenceDimension) return phaseText('propose:' + evidenceDimension[1].replaceAll(' ', '_'), t);
  const systemMessage = systemMessages[message.trim()];
  if (systemMessage) return t(...systemMessage);
  if (/^(pausing|stopping|waiting|paused|stopped|continuing)\b/i.test(message.trim())) return message;
  const proposal = /^propose pool:\s*([a-z_]+)(?:\s*\(slice (\d+)\/(\d+)\))?$/i.exec(message.trim());
  if (proposal) {
    const dimensions: Record<string, [string, string]> = {
      target_coverage: ['Developing target criteria', '正在生成靶点标准'],
      oral_bioavailability: ['Developing oral bioavailability criteria', '正在生成口服生物利用度标准'],
      metabolic_stability: ['Developing metabolic stability criteria', '正在生成代谢稳定性标准'],
      toxicological_safety: ['Developing safety criteria', '正在生成安全性标准'],
      physicochemical_properties: ['Developing physicochemical criteria', '正在生成理化性质标准'],
      pharmacokinetics: ['Developing pharmacokinetic criteria', '正在生成药代动力学标准'],
    };
    const label = dimensions[proposal[1]];
    const activity = label ? t(...label) : phaseText('propose', t);
    return activity + (proposal[2] && proposal[3] ? t(` · evidence batch ${proposal[2]} of ${proposal[3]}`, ` · 证据批次 ${proposal[2]} / ${proposal[3]}`) : '');
  }
  const batch = /^(.*?)\s+\(batch (\d+)\/(\d+)\)$/.exec(message.trim());
  if (batch && poolStages[batch[1]]) return phaseText(poolStages[batch[1]], t) + t(` · batch ${batch[2]} of ${batch[3]}`, ` · 批次 ${batch[2]} / ${batch[3]}`);
  if (poolStages[message.trim()]) return phaseText(poolStages[message.trim()], t);
  const stage = /^([a-z_]+(?::[a-z_]+)?)\s*·\s*iteration\s+(\d+)$/i.exec(message.trim());
  if (stage) {
    const aliases: Record<string, string> = { enumerate: 'evidence', critic: 'review', critique: 'review' };
    const label = phaseText(aliases[stage[1]] || stage[1], t);
    if (label !== stage[1]) return label + (Number(stage[2]) > 0 ? t(` · iteration ${stage[2]}`, ` · 迭代 ${stage[2]}`) : '');
  }
  if (/^claim admitted:/i.test(message)) return t('Reading the recorded evidence for this assessment', '正在读取本次评估的已有证据');
  if (/^cand_\S+\s*·\s*attr_\S+:\s*\w+/.test(message)) return t('Checking candidate evidence against the saved criteria', '正在按已保存的标准核查候选证据');
  return message || phaseText(workflow.phase, t);
}
export function ProgressRail({ workflow, connection, onUpdate, onResults, showResults = true }: { workflow: Workflow | null; connection: string; onUpdate: (value: Workflow) => void; onResults?: (task: string, snapshot: string) => void; showResults?: boolean }) {
  const { t } = useI18n();
  const [now, setNow] = useState(Date.now());
  const [busy, setBusy] = useState(false), [error, setError] = useState(''), [confirmStop, setConfirmStop] = useState(false);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [detailsOpen, setDetailsOpen] = useState(false);
  const detailsId = useId();
  useEffect(() => { const timer = setInterval(() => setNow(Date.now()), 1000); return () => clearInterval(timer); }, []);
  useEffect(() => { setAnswers({}); setConfirmStop(false); setError(''); setDetailsOpen(false); }, [workflow?.workflow_id]);
  if (!workflow) return null;
  const progress = workflow.progress;
  const known = progress?.planned != null && progress.planned > 0 && progress.denominator_kind !== 'unknown' && progress.denominator_kind != null;
  const showCount = progress?.completed != null && (known || progress.completed > 0);
  const percentage = known && progress.completed != null ? Math.max(0, Math.min(100, progress.completed / progress.planned! * 100)) : null;
  const shownPercent = percentage == null ? null : Math.floor(percentage);
  const preparingResults = workflow.state === 'running' && workflow.phase === 'screen'
    && progress.scope === 'stage:assess' && percentage === 100;
  const active = ['queued', 'running', 'waiting_input', 'paused'].includes(workflow.state);
  const evidenceBatches = progress.scope === 'proposal_batches';
  const activityUnit = evidenceBatches ? t('Evidence batches', '证据批次') : progress.scope?.includes('identity') ? t('Candidate identities', '候选身份') : workflow.phase === 'screen' ? t('Candidate assessments', '候选评估单元') : t('Current activity', '当前活动');
  const compact = workflow.state === 'completed';
  const activityAge = elapsed(workflow.last_activity_at || workflow.updated_at, undefined, now);
  const cost = <span className="progress-cost">{workflow.budget?.used_usd == null || workflow.budget.cost_status === 'unknown' ? t('Cost not yet recorded', '费用尚未记录') : `${workflow.budget.cost_status === 'partial' ? t('Recorded subtotal', '已记录小计') : t('Estimated cost', '估计费用')} $${workflow.budget.used_usd.toFixed(4)}`}{workflow.budget?.limit_usd != null && ` / $${valueText(workflow.budget.limit_usd)}`}</span>;
  const currentPhase = workflow.phases?.find(phase => phase.id === workflow.phase.split(':')[0]);
  const phaseElapsed = currentPhase?.started_at ? elapsed(currentPhase.started_at, currentPhase.finished_at, now) : '—';
  async function command(action: 'pause' | 'resume' | 'stop' | 'reevaluate') {
    if (busy) return; setBusy(true); setError('');
    try { onUpdate(await api.command(workflow!.workflow_id, action)); setConfirmStop(false); }
    catch (issue) { setError(issue instanceof Error ? issue.message : String(issue)); }
    finally { setBusy(false); }
  }
  return <section className={`progress-rail ${active ? 'active' : ''} ${compact ? 'compact' : ''}`} aria-label={t('Research progress', '研究进度')}>
    <div className="progress-top"><div className="progress-identity"><span className={`activity-dot ${workflow.state === 'running' ? 'pulse' : ''}`} /><div><div className="eyebrow">{t('Research progress', '研究进度')}</div><strong title={workflow.title}>{workflow.title}</strong></div><Badge state={workflow.state} /></div><div className="progress-actions"><span className="elapsed">{t('Elapsed', '耗时')} {elapsed(workflow.started_at, workflow.finished_at, now)}</span>{workflow.can_pause && <button disabled={busy} onClick={() => command('pause')}><Icon name="pause" size={14} />{t('Pause', '暂停')}</button>}{workflow.can_resume && <button disabled={busy} onClick={() => command('resume')}><Icon name="play" size={14} />{t('Resume', '继续')}</button>}{compact && showResults && workflow.task_id && workflow.snapshot_id && onResults && <button type="button" className="primary" onClick={() => onResults(workflow.task_id!, workflow.snapshot_id!)}>{t('View saved results', '查看已保存结果')}<Icon name="arrow" size={14} /></button>}{workflow.can_reevaluate && (compact && workflow.snapshot_id && onResults ? <details className="progress-more"><summary>{t('More actions', '更多操作')}</summary><button disabled={busy} onClick={() => command('reevaluate')}><Icon name="play" size={14} />{t('Evaluate saved criteria', '评估已保存标准')}</button></details> : <button disabled={busy} onClick={() => command('reevaluate')}><Icon name="play" size={14} />{t('Evaluate saved criteria', '评估已保存标准')}</button>)}{workflow.can_stop && <button disabled={busy} onClick={() => setConfirmStop(true)}><Icon name="stop" size={14} />{t('Stop', '停止')}</button>}</div></div>
    {compact && <div className="completed-run-summary">{cost}<button type="button" className="text-button run-details-toggle" aria-expanded={detailsOpen} aria-controls={detailsId} onClick={() => setDetailsOpen(value => !value)}>{detailsOpen ? t('Hide run details', '收起运行详情') : t('Workflow & run details', '流程与运行详情')}<Icon name="chevron" size={13} /></button></div>}
    <div id={detailsId} hidden={compact && !detailsOpen}><WorkflowStages workflow={workflow} />{compact && <Audit data={workflow} title={t('Run record', '运行记录')} />}</div>
    {!compact && <div className="activity-panel"><div className="activity-panel-heading"><div><span className="activity-label">{phaseText(workflow.active_stage || workflow.phase, t)}</span><p aria-live="polite">{preparingResults ? t('Preparing results from the completed assessments', '逐项评估已完成，正在整理结果') : progressMessage(workflow, t)}</p></div><div className="activity-count">{showCount ? <><strong>{progress.completed!.toLocaleString()}{known && <small> / {progress.planned!.toLocaleString()}</small>}</strong><span>{percentage != null ? `${shownPercent}% · ${activityUnit}` : t('completed; remaining work not yet known', '已完成；剩余工作量尚未确定')}</span></> : <span>{workflow.state === 'running' ? t('Working · workload not yet known', '处理中 · 工作量尚未确定') : stateText(workflow.state, t)}</span>}</div></div><div className={`progress-track ${percentage == null && workflow.state === 'running' ? 'indeterminate' : ''}`} role="progressbar" aria-label={t('Current activity progress', '当前活动进度')} aria-valuenow={shownPercent ?? undefined} aria-valuemin={0} aria-valuemax={100}>{percentage != null && <div style={{ width: `${percentage}%` }} />}</div><div className="activity-facts">{evidenceBatches && workflow.batch && <span>{t('Evidence batch', '证据批次')} {workflow.batch.batch_index} / {workflow.batch.batch_count} · {workflow.batch.source_claim_count.toLocaleString()} {t('saved claims', '条已保存证据')}</span>}{workflow.iteration != null && workflow.iteration > 0 && <span>{t('Round', '轮次')} {workflow.iteration}</span>}{workflow.active_criteria_count != null && <span>{t('After last completed stage', '上一完成阶段')} <strong>{workflow.active_criteria_count.toLocaleString()}</strong></span>}{workflow.last_stage_change && (workflow.last_stage_change.before != null || workflow.last_stage_change.after != null) && <span>{t('Last stage', '上一阶段')} · {phaseText(workflow.last_stage_change.stage, t)} {valueText(workflow.last_stage_change.before)} → {valueText(workflow.last_stage_change.after)}</span>}</div><div className="activity-panel-meta"><span title={t('Elapsed time for all activities in this workflow phase.', '此流程阶段内所有活动的累计耗时。')}>{phaseText(workflow.phase, t)} · {t('elapsed', '累计耗时')} {phaseElapsed}</span><span>{activityAge === '—' ? t('Last activity not recorded', '最近活动尚未记录') : t(`Last activity ${activityAge} ago`, `最近活动距今 ${activityAge}`)}</span></div></div>}
    {workflow.state === 'paused' && <p className="subtle">{t('Research is paused. Completed records are retained.', '研究已暂停，已完成记录会保留。')}</p>}
    {workflow.state === 'waiting_input' && workflow.questions?.length > 0 && <form className="question-form" onSubmit={async event => { event.preventDefault(); setBusy(true); setError(''); try { onUpdate(await api.answer(workflow.workflow_id, answers)); } catch (issue) { setError(String(issue)); } finally { setBusy(false); } }}>{workflow.questions.map(question => <label key={question.id}>{question.prompt}<textarea value={answers[question.id] || ''} onChange={event => setAnswers(previous => ({ ...previous, [question.id]: event.target.value }))} required rows={2} /></label>)}<button className="primary" disabled={busy}>{t('Send answers and continue', '提交信息并继续')}</button></form>}
    {confirmStop && <div className="inline-confirm"><p>{t('Stop this research? Completed work will stay available.', '停止这项研究？已完成的工作会继续保留。')}</p><button className="danger-button" disabled={busy} onClick={() => command('stop')}>{t('Stop research', '停止研究')}</button><button onClick={() => setConfirmStop(false)}>{t('Keep running', '继续运行')}</button></div>}
    {error && <p className="inline-error" role="alert">{error}</p>}
    {workflow.error && <p className="inline-error" role="alert">{typeof workflow.error === 'string' ? workflow.error : workflow.error.message}</p>}
    {!compact && <><div className="progress-foot"><span className={`connection ${connection}`}><i />{connection === 'live' ? t('Live updates', '实时更新') : connection === 'polling' ? t('Reconnecting · checking every 2 seconds', '正在重连 · 每两秒检查状态') : t('Connecting to updates', '正在连接状态更新')}</span>{cost}{workflow.budget?.cost_status === 'partial' && <span>{t('Known subtotal; some costs are not yet recorded.', '已知小计；部分费用尚未记录。')}</span>}</div><Audit data={workflow} title={t('Run record', '运行记录')} /></>}
  </section>;
}
