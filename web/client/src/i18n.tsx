import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';

type Language = 'en' | 'zh';
type Translate = (english: string, chinese: string) => string;
const Context = createContext<{ language: Language; setLanguage: (value: Language) => void; t: Translate }>({ language: 'en', setLanguage: () => {}, t: en => en });
function savedLanguage(): Language {
  const requested = new URLSearchParams(location.search).get('lang');
  if (requested === 'en' || requested === 'zh') return requested;
  try { return localStorage.getItem('mas.language') === 'zh' ? 'zh' : 'en'; } catch { return 'en'; }
}
export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguage] = useState<Language>(savedLanguage);
  useEffect(() => {
    const pop = () => { const value = new URLSearchParams(location.search).get('lang'); if (value === 'en' || value === 'zh') setLanguage(value); };
    addEventListener('popstate', pop); return () => removeEventListener('popstate', pop);
  }, []);
  useEffect(() => {
    document.documentElement.lang = language === 'zh' ? 'zh-CN' : 'en';
    try { localStorage.setItem('mas.language', language); } catch { /* Preference storage is optional. */ }
    const url = new URL(location.href); url.searchParams.set('lang', language);
    history.replaceState(history.state, '', url);
  }, [language]);
  const t = useCallback<Translate>((en, zh) => language === 'zh' ? zh : en, [language]);
  const value = useMemo(() => ({ language, setLanguage, t }), [language, t]);
  return <Context.Provider value={value}>{children}</Context.Provider>;
}
export function useI18n() { return useContext(Context); }
export function operationText(operation: string, t: Translate): string {
  const labels: Record<string, [string, string]> = {
    register: ['Registered', '已注册'], add: ['Added', '已新增'], revise: ['Revised', '已修改'],
    merge: ['Merged', '已合并'], consolidate: ['Consolidated', '已整合'], remove: ['Removed', '已撤回'],
    reinstate: ['Restored', '已恢复'], promote: ['Registered', '已注册'], defer: ['Deferred', '已延后'],
  };
  const pair = labels[operation];
  return pair ? t(...pair) : operation;
}
export function stateText(state: string | undefined, t: Translate): string {
  const labels: Record<string, [string, string]> = {
    draft: ['Draft', '草稿'], queued: ['Queued', '排队中'], running: ['Running', '运行中'], waiting_input: ['Your input needed', '需要补充信息'],
    paused: ['Paused', '已暂停'], completed: ['Completed', '已完成'], unresolved: ['Needs attention', '需要处理'], failed: ['Failed', '失败'], cancelled: ['Stopped', '已停止'], interrupted: ['Interrupted', '已中断'],
    qualified: ['Qualified', '符合要求'], pending: ['Pending evidence', '证据待完善'], rejected: ['Rejected', '已淘汰'], unassessed: ['Not assessed', '尚未评估'],
    in_evaluation: ['In evaluation', '参与评估'],
    active: ['Active', '当前使用'], candidate: ['Proposed', '提议中'], proposed: ['Proposed', '已提出'], retained: ['Retained', '已保留'], merged: ['Merged', '已合并'], retired: ['Retired', '已撤回'], withdrawn: ['Withdrawn', '已撤回'], superseded: ['Earlier version', '早期版本'],
    registered: ['Registered', '已注册'], promoted: ['Registered', '已注册'], filtered_out: ['Filtered out', '已筛除'], merged_away: ['Merged', '已合并'],
    needs_refine: ['Needs refinement', '待完善'], deferred_next_round: ['Deferred', '延后处理'], capability_deferred: ['Evidence deferred', '证据延后处理'], needs_human_review: ['Review needed', '需要复核'],
    hard_exclusion: ['Required', '必需'], hard: ['Required', '必需'], preference: ['Preference', '偏好'], screening: ['Screening', '筛选'],
    exploratory_consideration: ['Context', '参考考量'],
    higher_better: ['Higher is better', '越高越好'], lower_better: ['Lower is better', '越低越好'], within_range: ['Within a range', '在范围内'],
    target_value: ['Near a target value', '接近目标值'], non_directional: ['No ordering preference', '无排序偏好'], undetermined: ['Not determined', '尚未确定'], unassigned: ['Not assigned', '尚未分配'],
    available: ['Value available', '已有数值'], unknown_missing: ['Missing evidence', '缺少证据'], unknown_conflicted: ['Conflicting evidence', '证据冲突'], not_assessed: ['Not assessed', '尚未评估'], inapplicable: ['Not applicable', '不适用'], simulated: ['Simulated', '模拟'],
    unknown_unresolvable: ['Interpretation needed', '需明确判读方法'],
    measured: ['Measured', '实测'], predicted: ['Predicted', '预测'], curated: ['Curated', '数据库记录'], unknown: ['Unknown', '未知'],
    derived: ['Derived result', '推导结果'], asserted: ['Reported statement', '来源陈述'], absent: ['No value', '暂无数值'],
    peer_reviewed: ['Peer-reviewed source', '同行评审来源'], full_text: ['Full text', '全文'], abstract: ['Abstract', '摘要'],
    unverified: ['Not verified', '未经核验'], verified: ['Verified', '已核验'],
    pass: ['Met', '满足'], fail: ['Not met', '未满足'], provisional: ['Provisional', '暂定'], confirmed: ['Confirmed', '已确认'],
    ready: ['Ready', '已就绪'], syncing: ['Updating records', '更新记录中'], not_started: ['Not started', '尚未开始'],
  };
  const pair = labels[state || ''];
  return pair ? t(...pair) : state || '—';
}
export function phaseText(phase: string | undefined, t: Translate): string {
  if (phase?.startsWith('propose:')) {
    const dimensions: Record<string, [string, string]> = {
      target_coverage: ['Target coverage', '靶点覆盖'], oral_bioavailability: ['Oral bioavailability', '口服生物利用度'],
      metabolic_stability: ['Metabolic stability', '代谢稳定性'], toxicological_safety: ['Toxicological safety', '毒理安全性'],
      physicochemical_properties: ['Physicochemical properties', '理化性质'], pharmacokinetics: ['Pharmacokinetics', '药代动力学'],
    };
    const dimension = dimensions[phase.slice('propose:'.length)];
    return t('Generate criteria', '生成标准') + (dimension ? ` · ${t(...dimension)}` : '');
  }
  const labels: Record<string, [string, string]> = {
    task: ['Define the research', '明确研究目标'], evidence: ['Prepare evidence', '准备证据'], propose: ['Generate criteria', '生成标准'],
    refine: ['Refine criteria', '整理标准'], review: ['Review criteria', '复核标准'], freeze: ['Prepare evaluation', '准备评估'],
    screen: ['Assess candidates', '评估候选'], results: ['Save results', '保存结果'],
    filter: ['Filter', '筛查'], distill: ['Distill', '提炼'], merge: ['Merge', '合并'], promote: ['Register', '注册'], reenter: ['Bring forward', '接入'],
    mandated: ['Task requirements', '任务要求'], task_requirements: ['Task requirements', '任务要求'],
  };
  const pair = labels[phase || ''];
  return pair ? t(...pair) : phase || '—';
}
