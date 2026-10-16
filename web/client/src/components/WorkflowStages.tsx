import { useEffect, useRef } from 'react';
import type { Workflow } from '../api/types';
import { stateText, useI18n } from '../i18n';
import { Icon } from './UI';

const steps = [
  { id: 'task', en: 'Goal', zh: '目标' }, { id: 'evidence', en: 'Evidence', zh: '证据' },
  { id: 'propose', en: 'Develop', zh: '展开' }, { id: 'refine', en: 'Refine', zh: '提炼' },
  { id: 'review', en: 'Review', zh: '复核' }, { id: 'freeze', en: 'Prepare', zh: '准备' },
  { id: 'screen', en: 'Evaluate', zh: '评估' }, { id: 'results', en: 'Results', zh: '结果' },
];

export function workflowStages(workflow: Workflow) {
  const aliases: Record<string, string> = { identity: 'screen', assess: 'screen', snapshot: 'results' };
  const phase = aliases[workflow.phase] || workflow.phase.split(':')[0];
  return steps.map(step => {
    const record = workflow.phases?.find(item => item.id === step.id);
    const current = step.id === phase && ['queued', 'running', 'paused', 'waiting_input'].includes(workflow.state);
    const stoppedHere = step.id === phase && record?.state === 'running' && ['cancelled', 'failed', 'unresolved'].includes(workflow.state);
    const state = current || stoppedHere ? workflow.state : record?.state || 'not_started';
    return { ...step, state, current };
  });
}

export function WorkflowStages({ workflow }: { workflow: Workflow }) {
  const { t } = useI18n();
  const track = useRef<HTMLOListElement>(null);
  const stages = workflowStages(workflow);
  const current = stages.find(item => item.current)?.id;
  const completed = stages.filter(item => item.state === 'completed').length;
  useEffect(() => {
    const container = track.current;
    const node = container?.querySelector<HTMLElement>('[aria-current="step"]');
    if (!container || !node) return;
    const reveal = () => {
      if (container.scrollWidth > container.clientWidth) {
        container.scrollTo({ left: node.offsetLeft - (container.clientWidth - node.clientWidth) / 2, behavior: 'auto' });
      }
    };
    reveal();
    const observer = new ResizeObserver(reveal);
    observer.observe(container);
    return () => observer.disconnect();
  }, [workflow.workflow_id, current]);
  return <div className="workflow-stages"><div className="workflow-stages-caption"><span>{t('Research workflow', '研究流程')}</span><strong>{completed} / {stages.length} {t('stages completed', '个阶段已完成')}</strong></div><ol ref={track} className="workflow-stage-track" aria-label={t('Research workflow stages', '研究流程阶段')}>{stages.map((stage, index) => <li key={stage.id} className={`${stage.state} ${stage.current ? 'current' : ''}`} aria-current={stage.current ? 'step' : undefined}><span className="workflow-step-marker">{stage.state === 'completed' ? <Icon name="check" size={14} /> : index + 1}</span><span className="workflow-step-copy"><strong>{t(stage.en, stage.zh)}</strong><small>{stateText(stage.state, t)}</small></span></li>)}</ol></div>;
}
