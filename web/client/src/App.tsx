import { useCallback, useEffect, useRef, useState, type MouseEvent } from 'react';
import { api, setOperationToken } from './api/client';
import type { Draft, RevisionResult, TaskInput, Workflow } from './api/types';
import { useI18n } from './i18n';
import { routeHref, useRoute, type View } from './hooks/useRoute';
import { projectionReady, useBootstrap } from './hooks/useBootstrap';
import { useWorkflowStream } from './hooks/useWorkflowStream';
import { visibleWorkflow } from './hooks/workflowContext';
import { Drawer, Empty, ErrorNotice, Icon, Loading, Panel } from './components/UI';
import { GoalComposer } from './components/GoalComposer';
import { ProgressRail } from './components/ProgressRail';
import { OverviewPage } from './pages/OverviewPage';
import { CriteriaPage } from './pages/CriteriaPage';
import { CandidatesPage } from './pages/CandidatesPage';
import { EvidencePage } from './pages/EvidencePage';
import { SettingsPage } from './pages/SettingsPage';

export default function App() {
  const { language, setLanguage, t } = useI18n();
  const { route, navigate } = useRoute();
  const bootstrap = useBootstrap();
  const stream = useWorkflowStream(bootstrap.data?.workflows, !!bootstrap.data);
  const [composerInput, setComposerInput] = useState<TaskInput>();
  const [composerWithData, setComposerWithData] = useState(false);
  const [composerOpen, setComposerOpen] = useState(false), [feedback, setFeedback] = useState('');
  const [followWorkflow, setFollowWorkflow] = useState(() => {
    if (route.task) return '';
    try { return sessionStorage.getItem('mas.pendingWorkflow') || ''; } catch { return ''; }
  });
  const [viewRevision, setViewRevision] = useState(0);
  const selectionInitialized = useRef(false);
  useEffect(() => { if (bootstrap.data) setOperationToken(bootstrap.data.operation_token); }, [bootstrap.data]);
  useEffect(() => {
    if (!bootstrap.data || selectionInitialized.current) return;
    if (followWorkflow) { selectionInitialized.current = true; return; }
    if (!route.task && !bootstrap.data.tasks.length && !projectionReady(bootstrap.data.projection)) return;
    selectionInitialized.current = true;
    if (!route.task) {
      let saved = ''; try { saved = localStorage.getItem('mas.selectedTask') || ''; } catch { /* URL remains the source of selection. */ }
      const preferred = [saved, bootstrap.data.current_task_id, bootstrap.data.tasks[0]?.task_id].find(id => id && bootstrap.data!.tasks.some(task => task.task_id === id));
      if (preferred) navigate({ task: preferred, item: '', snapshot: '' }, true);
    }
  }, [bootstrap.data, route.task, followWorkflow, navigate]);
  useEffect(() => {
    try { if (followWorkflow) sessionStorage.setItem('mas.pendingWorkflow', followWorkflow); else sessionStorage.removeItem('mas.pendingWorkflow'); } catch { /* Live following also works without session storage. */ }
  }, [followWorkflow]);
  useEffect(() => { if (route.task) try { localStorage.setItem('mas.selectedTask', route.task); } catch { /* Selection is also in the URL. */ } }, [route.task]);
  useEffect(() => {
    if (!followWorkflow) return;
    const workflow = stream.workflows.find(item => item.workflow_id === followWorkflow);
    if (workflow?.task_id) { navigate({ task: workflow.task_id, view: 'overview', item: '', snapshot: '', criterion: '', candidate: '', source: '' }); setFollowWorkflow(''); bootstrap.refresh(); }
  }, [followWorkflow, stream.workflows, navigate, bootstrap.refresh]);
  // Coalesce event bursts; visible research data refreshes without replacing the page.
  useEffect(() => { const timer = setTimeout(() => setViewRevision(value => value + 1), 400); return () => clearTimeout(timer); }, [stream.revision]);
  const chooseTask = useCallback((task: string) => { setFollowWorkflow(''); setFeedback(''); navigate({ task, item: '', snapshot: '', criterion: '', candidate: '', source: '' }); }, [navigate]);
  const closeDetails = useCallback(() => navigate({ item: '' }), [navigate]);
  const go = (view: View) => navigate({ view, item: '', criterion: '', candidate: '', source: '' });
  const onDraftSaved = (_draft: Draft) => bootstrap.refresh();
  function newResearch(withData = false) { setComposerInput(undefined); setComposerWithData(withData); setComposerOpen(true); }
  function launched(workflow: Workflow) {
    stream.upsert(workflow); setComposerOpen(false); setFeedback(''); bootstrap.refresh();
    setFollowWorkflow(workflow.task_id ? '' : workflow.workflow_id);
    navigate({ task: workflow.task_id || '', view: 'overview', item: '', snapshot: '', criterion: '', candidate: '', source: '' });
  }
  function revised(result: RevisionResult) {
    setFeedback(result.message); if (result.workflow) stream.upsert(result.workflow);
    if (result.task_id && result.task_id !== route.task) chooseTask(result.task_id);
    setViewRevision(value => value + 1); bootstrap.refresh();
  }
  async function editSelectedTask() {
    try {
      const detail = await api.overview(route.task);
      if (detail.input) { setComposerInput({ ...detail.input, revision_of_task_id: route.task }); setComposerWithData(false); setComposerOpen(true); }
      else { go('overview'); setFeedback(t('The saved task input is not available yet.', '此任务的已保存输入尚不可用。')); }
    } catch (issue) { setFeedback(issue instanceof Error ? issue.message : String(issue)); }
  }
  function navClick(event: MouseEvent<HTMLAnchorElement>, view: View) {
    if (event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    event.preventDefault(); go(view);
  }
  const links: { view: View; label: string }[] = [
    { view: 'overview', label: t('Overview', '总览') }, { view: 'criteria', label: t('Criteria', '标准') },
    { view: 'candidates', label: t('Candidates', '候选') }, { view: 'evidence', label: t('Evidence', '证据') }, { view: 'settings', label: t('Settings', '设置') },
  ];
  const data = bootstrap.data;
  const enabled = data?.operations_enabled !== false && !!data?.operation_token;
  const selectedTask = data?.tasks.find(task => task.task_id === route.task);
  const currentWorkflows = stream.workflows.filter(workflow => workflow.task_id === route.task);
  const workflow = visibleWorkflow(stream.workflows, route.task, followWorkflow);
  const otherActiveWorkflow = stream.workflows.find(item => item.workflow_id !== workflow?.workflow_id && item.task_id !== route.task && ['queued', 'running', 'paused', 'waiting_input'].includes(item.state));
  const creating = !!followWorkflow && !workflow?.task_id;
  const creationTitle = workflow?.title || t('Starting your research', '正在开始研究');
  const creationMessage = !workflow ? t('Connecting to the new research progress.', '正在连接新研究进度。')
    : workflow.state === 'paused' ? t('Research is paused. Resume above when you are ready.', '研究已暂停，准备好后可在上方继续。')
    : workflow.state === 'waiting_input' ? t('Answer the questions above to continue preparing this research.', '请回答上方问题，继续准备这项研究。')
    : workflow.state === 'cancelled' ? t('Research stopped. Saved work remains available.', '研究已停止，已保存的工作会保留。')
    : workflow.state === 'failed' || workflow.state === 'unresolved' ? t('Review the progress message above to continue this research.', '查看上方进度信息，继续处理这项研究。')
    : t('Preparing the research workspace. It will open here automatically when ready.', '正在准备研究工作区，就绪后会自动在此打开。');
  const bootstrapPending = !!data && (!projectionReady(data.projection)
    || stream.workflows.some(item => item.task_id && !data.tasks.some(task => task.task_id === item.task_id)));
  useEffect(() => {
    if (!bootstrapPending || bootstrap.loading) return;
    const timer = setTimeout(bootstrap.refresh, 5000);
    return () => clearTimeout(timer);
  }, [bootstrapPending, bootstrap.loading, bootstrap.data, bootstrap.error, bootstrap.refresh]);

  return <div className="app-shell"><a className="skip-link" href="#main-content">{t('Skip to content', '跳转至内容')}</a><aside className="sidebar"><a className="brand" href={routeHref({ task: route.task, view: 'overview' }, language)} onClick={event => navClick(event, 'overview')}><span className="brand-mark"><svg viewBox="0 0 36 36" fill="none" aria-hidden="true"><path d="m18 3 15 15-15 15L3 18Z" stroke="currentColor" strokeWidth="1.3"/><path d="M10 11h16L18 28 10 11Zm0 0 8 7 8-7M18 18v10" stroke="currentColor" strokeWidth="1.4"/><circle cx="10" cy="11" r="2.7" fill="currentColor"/><circle cx="26" cy="11" r="2.7" fill="currentColor"/><circle cx="18" cy="28" r="2.7" fill="currentColor"/></svg></span><span>MAS <em>Research</em><small>{t('A research workbench', '科研工作台')}</small></span></a><button className="new-research" disabled={!enabled} onClick={() => newResearch()}><Icon name="plus" size={16} />{t('New research', '新建研究')}</button><div className="sidebar-section"><label htmlFor="task-select">{t('Current research', '当前研究')}</label><select id="task-select" value={route.task} onChange={event => chooseTask(event.target.value)}><option value="" disabled>{creating ? `${t('Creating', '正在创建')} · ${creationTitle}` : t('Choose a research task', '选择研究任务')}</option>{data?.tasks.map(task => <option key={task.task_id} value={task.task_id}>{task.title || task.objective.slice(0, 80)}</option>)}{route.task && !selectedTask && <option value={route.task}>{currentWorkflows[0]?.title || t('Selected research', '已选研究')}</option>}</select></div><nav aria-label={t('Research pages', '研究页面')}>{links.map(link => <a key={link.view} href={routeHref({ view: link.view, task: route.task, snapshot: route.snapshot }, language)} onClick={event => navClick(event, link.view)} aria-current={route.view === link.view ? 'page' : undefined}><Icon name={link.view} /><span>{link.label}</span><Icon name="chevron" size={13} /></a>)}</nav><div className="sidebar-bottom"><span className="environment-dot" />{t('Research workspace', '研究工作区')}</div></aside>
    <div className="workspace"><header className="topbar"><div className="breadcrumb">{t('Workspace', '工作区')}<span>/</span><strong>{creating && route.view !== 'settings' ? t('Preparing research', '正在准备研究') : links.find(link => link.view === route.view)?.label}</strong></div><div className="topbar-actions">{(!data || !projectionReady(data.projection)) && <span className="projection-state" role="status">{data ? t('Updating research…', '正在更新研究…') : t('Connecting…', '正在连接…')}</span>}<div className="language-switch" role="group" aria-label={t('Interface language', '界面语言')}><button aria-pressed={language === 'en'} onClick={() => setLanguage('en')}>English</button><button aria-pressed={language === 'zh'} onClick={() => setLanguage('zh')}>中文</button></div></div></header><div className={`progress-container ${workflow?.state === 'completed' ? 'settled' : ''}`}><ProgressRail workflow={workflow} showResults={route.view !== 'overview' && route.view !== 'candidates'} connection={stream.connection} onUpdate={stream.upsert} onResults={(task, snapshot) => { setFollowWorkflow(''); navigate({ task, view: 'candidates', snapshot, item: '', criterion: '', candidate: '', source: '' }); }} />{otherActiveWorkflow && <div className="other-research"><span>{t('Other research in progress', '其他进行中的研究')} · <strong>{otherActiveWorkflow.title}</strong></span><button type="button" className="text-button" onClick={() => { setFollowWorkflow(otherActiveWorkflow.task_id ? '' : otherActiveWorkflow.workflow_id); navigate({ task: otherActiveWorkflow.task_id || '', view: 'overview', item: '', snapshot: '', criterion: '', candidate: '', source: '' }); }}>{t('Open progress', '查看进度')} →</button></div>}</div><main id="main-content" key={route.task || 'no-task'}>
      <ErrorNotice message={bootstrap.error} retry={bootstrap.refresh} />{!data ? bootstrap.loading && <Loading /> : <>{feedback && <p className="notice" role="status">{feedback}</p>}{route.view === 'settings' ? <SettingsPage enabled={enabled} onSaved={bootstrap.refresh} /> : creating ? <section className="research-creating" aria-live="polite"><div className="eyebrow">{t('New research', '新研究')}</div><h1>{creationTitle}</h1><p>{creationMessage}</p><p className="subtle">{t('The progress above belongs to this new research.', '上方进度对应这项新研究。')}</p></section> : !route.task ? <><section className="welcome-heading"><div className="eyebrow">{t('Make room for a better question', '从一个好问题开始')}</div><h1>{t('What will you investigate next?', '下一项研究，从哪里开始？')}</h1><p>{t('Define your objective. Follow the criteria. Inspect the evidence.', '明确目标，追踪标准，检查证据。')}</p></section>{enabled ? <Panel><GoalComposer bootstrap={data} onSaved={onDraftSaved} onLaunched={launched} onDataChanged={bootstrap.refresh} /></Panel> : <Empty title={t('Choose a research task to begin', '选择研究任务开始查看')}><p>{t('Choose a task to explore its questions, criteria and evidence.', '选择任务，查看研究问题、标准和证据。')}</p></Empty>}</> : route.view === 'overview' ? <OverviewPage task={route.task} revision={viewRevision} enabled={enabled} libraries={data.libraries} evidenceSources={data.evidence_sources} onResults={snapshot => navigate({ view: 'candidates', snapshot, item: '', criterion: '', candidate: '', source: '' })} onNavigate={navigate} onOwnData={() => newResearch(true)} onNewWithSetup={input => { setComposerInput(input); setComposerWithData(false); setComposerOpen(true); }} onCriteria={() => go('criteria')} onEdit={input => { setComposerInput({ ...input, revision_of_task_id: route.task }); setComposerWithData(false); setComposerOpen(true); }} /> : route.view === 'criteria' ? <CriteriaPage task={route.task} snapshot={route.snapshot} onNavigate={navigate} item={route.item} revision={viewRevision} enabled={enabled} onOpen={item => navigate({ item })} onClose={closeDetails} onRevision={revised} onEditTask={() => { void editSelectedTask(); }} /> : route.view === 'candidates' ? <CandidatesPage task={route.task} onNavigate={navigate} item={route.item} snapshot={route.snapshot} revision={viewRevision} onOpen={item => navigate({ item })} onClose={closeDetails} onSnapshot={snapshot => navigate({ snapshot, item: '' })} /> : <EvidencePage task={route.task} revision={viewRevision} route={route} onNavigate={navigate} />}</>}
    </main><footer className="workspace-footer">MAS · {t('Built around recorded research', '以真实研究记录为依据')}<button className="text-button" onClick={() => { bootstrap.refresh(); setViewRevision(value => value + 1); }}><Icon name="refresh" size={12} />{t('Refresh records', '刷新记录')}</button></footer></div>
    {composerOpen && data && <Drawer title={composerInput?.revision_of_task_id ? t('Edit task as a new version', '编辑任务并创建新版本') : composerInput ? t('New study with this setup', '按此设置新建研究') : t('Start a new research task', '开始一项新研究')} onClose={() => setComposerOpen(false)}>{composerInput && !composerInput.revision_of_task_id && <p className="notice">{t('Reuses the setup and saved evidence; criteria start empty.', '沿用研究设置和已保存证据；标准从空集合开始生成。')}</p>}<GoalComposer bootstrap={data} initialInput={composerInput} startWithData={composerWithData} onSaved={onDraftSaved} onLaunched={launched} onDataChanged={bootstrap.refresh} /></Drawer>}
  </div>;
}
