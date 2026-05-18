import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { api, type AgentDefinition, type AgentWorkflow, type WorkflowEdge, type WorkflowNode, type WorkflowVersion } from '../../lib/api'

type Draft = Omit<AgentDefinition, 'id'>
type JsonField = 'modelConfig' | 'inputSchema' | 'outputSchema' | 'normalizedInputSchema' | 'normalizedOutputSchema' | 'inputMapping' | 'outputMapping' | 'toolPolicy' | 'constraints' | 'runtimePolicy'
type Workspace = 'agents' | 'workflows' | 'runs'
type EditorMode = 'guided' | 'expert'
type AgentFilter = 'all' | 'active' | 'draft'
type SaveState = 'saved' | 'modified' | 'saving'

const EMPTY_DRAFT: Draft = {
  name: '', role: '', avatar: 'A', description: '', objective: '', downstreamHint: '', autonomy: 'supervised', status: 'active',
  modelConfig: { provider: 'openai', model: 'gpt-5.4', temperature: 0.2, topP: 1, maxTokens: 4096 },
  systemPrompt: '', userPromptTemplate: '',
  inputSchema: { type: 'object', properties: {}, required: [] }, outputSchema: { type: 'object', properties: {}, required: [] },
  normalizedInputSchema: { type: 'object', properties: {}, required: [] }, normalizedOutputSchema: { type: 'object', properties: {}, required: [] },
  inputMapping: [], outputMapping: [], toolPolicy: [], constraints: [], runtimePolicy: { timeoutSeconds: 120, maxRetries: 2, retryBackoffSeconds: 5, humanApprovalRequired: false },
}
const STEPS = ['基础信息', '模型与提示词', '原始输入输出', '标准化结构', '映射与约束']
const MODEL_OPTIONS = ['gpt-5.4', 'gpt-5.2', 'gpt-5.4-mini', 'claude-sonnet-4', 'deepseek-v3']

function pretty(v: unknown) { return JSON.stringify(v, null, 2) }
function parseJson<T>(value: string, label: string): T { try { return JSON.parse(value) as T } catch { throw new Error(`${label} 不是合法 JSON`) } }
function agentPayload(agent: Draft): Draft { return agent }

export default function Agent(_props: { onNavigate?: (target: string) => void; onModal?: (target: string) => void }) {
  const [agents, setAgents] = useState<AgentDefinition[]>([])
  const [workflows, setWorkflows] = useState<AgentWorkflow[]>([])
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null)
  const [selectedWorkflowId, setSelectedWorkflowId] = useState<string | null>(null)
  const [draft, setDraft] = useState<Draft>(EMPTY_DRAFT)
  const [jsonDrafts, setJsonDrafts] = useState<Record<JsonField, string>>(() => jsonTexts(EMPTY_DRAFT))
  const [step, setStep] = useState(0)
  const [editing, setEditing] = useState(true)
  const [message, setMessage] = useState('')
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null)
  const [connectFromId, setConnectFromId] = useState<string | null>(null)
  const [runPayload, setRunPayload] = useState('{\n  "payload": {}\n}')
  const [runResult, setRunResult] = useState<Record<string, unknown> | null>(null)
  const [running, setRunning] = useState(false)
  const [workflowVersions, setWorkflowVersions] = useState<WorkflowVersion[]>([])
  const [publishing, setPublishing] = useState(false)
  const [workspace, setWorkspace] = useState<Workspace>('agents')
  const [editorMode, setEditorMode] = useState<EditorMode>('guided')
  const [agentQuery, setAgentQuery] = useState('')
  const [agentFilter, setAgentFilter] = useState<AgentFilter>('all')
  const [saveState, setSaveState] = useState<SaveState>('saved')
  const [lastSavedAt, setLastSavedAt] = useState<string | null>(null)
  const [showNewAgent, setShowNewAgent] = useState(false)
  const [newAgentRole, setNewAgentRole] = useState('backtest')
  const [newAgentTemplateId, setNewAgentTemplateId] = useState('')
  const [newAgentName, setNewAgentName] = useState('')
  const canvasRef = useRef<HTMLDivElement>(null)

  function jsonTexts(a: Draft): Record<JsonField, string> {
    return {
      modelConfig: pretty(a.modelConfig), inputSchema: pretty(a.inputSchema), outputSchema: pretty(a.outputSchema),
      normalizedInputSchema: pretty(a.normalizedInputSchema), normalizedOutputSchema: pretty(a.normalizedOutputSchema),
      inputMapping: pretty(a.inputMapping), outputMapping: pretty(a.outputMapping), toolPolicy: pretty(a.toolPolicy),
      constraints: pretty(a.constraints), runtimePolicy: pretty(a.runtimePolicy),
    }
  }
  async function refresh() {
    const [defs, flows] = await Promise.all([api.agent.definitions(), api.agent.workflows()])
    setAgents(defs); setWorkflows(flows)
    if (!selectedWorkflowId && flows[0]) setSelectedWorkflowId(flows[0].id)
    if (!selectedAgentId && defs[0]) selectAgent(defs[0])
  }
  useEffect(() => { void refresh() }, [])
  useEffect(() => {
    if (!selectedWorkflowId) { setWorkflowVersions([]); return }
    void api.agent.workflowVersions(selectedWorkflowId).then(setWorkflowVersions)
  }, [selectedWorkflowId])
  function selectAgent(agent: AgentDefinition) {
    const { id: _id, ...rest } = agent
    setSelectedAgentId(agent.id); setDraft(rest); setJsonDrafts(jsonTexts(rest)); setEditing(true); setStep(0); setSaveState('saved')
  }
  function newAgent() { setShowNewAgent(true); setNewAgentTemplateId(''); setNewAgentName(''); setNewAgentRole('backtest') }
  function createAgentDraft() {
    const template = agents.find((agent) => agent.id === newAgentTemplateId)
    const base = template ? (({ id: _id, ...rest }) => rest)(template) : EMPTY_DRAFT
    const next = { ...base, name: newAgentName || `${capitalize(newAgentRole)} Agent`, role: newAgentRole, status: 'draft' }
    setSelectedAgentId(null); setDraft(next); setJsonDrafts(jsonTexts(next)); setEditing(true); setStep(0); setSaveState('modified'); setShowNewAgent(false)
  }
  function update<K extends keyof Draft>(key: K, value: Draft[K]) { setDraft((d) => ({ ...d, [key]: value })); setSaveState('modified') }
  function updateJson(field: JsonField, value: string) { setJsonDrafts((d) => ({ ...d, [field]: value })); setSaveState('modified') }
  async function saveAgent() {
    try {
      setSaveState('saving')
      const next = { ...draft }
      ;(Object.keys(jsonDrafts) as JsonField[]).forEach((field) => { ;(next as any)[field] = parseJson(jsonDrafts[field], field) })
      if (!next.name || !next.role) throw new Error('名称和角色不能为空')
      const saved = selectedAgentId ? await api.agent.updateDefinition(selectedAgentId, agentPayload(next)) : await api.agent.createDefinition(agentPayload(next))
      setMessage('Agent 已保存'); setLastSavedAt(new Date().toISOString()); await refresh(); selectAgent(saved)
    } catch (e) { setSaveState('modified'); setMessage(e instanceof Error ? e.message : '保存失败') }
  }
  const workflow = workflows.find((w) => w.id === selectedWorkflowId) ?? null
  const selectedNode = workflow?.nodes.find((n) => n.id === selectedNodeId) ?? null
  const selectedEdge = workflow?.edges.find((e) => e.id === selectedEdgeId) ?? null
  const agentById = useMemo(() => Object.fromEntries(agents.map((a) => [a.id, a])), [agents])
  async function saveWorkflow(next: AgentWorkflow) {
    const { id, ...payload } = next
    const saved = await api.agent.updateWorkflow(id, payload)
    setWorkflows((rows) => rows.map((w) => w.id === saved.id ? saved : w)); setMessage('工作流已保存')
  }
  async function addNode(agentId: string) {
    if (!workflow) return
    const n: WorkflowNode = { id: `tmp-${crypto.randomUUID()}`, agentDefinitionId: agentId, label: agentById[agentId]?.name ?? null, positionX: 40 + workflow.nodes.length * 36, positionY: 80 + workflow.nodes.length * 28, configOverride: {} }
    await saveWorkflow({ ...workflow, nodes: [...workflow.nodes, n] })
  }
  async function removeNode(nodeId: string) {
    if (!workflow) return
    await saveWorkflow({ ...workflow, nodes: workflow.nodes.filter((n) => n.id !== nodeId), edges: workflow.edges.filter((e) => e.sourceNodeId !== nodeId && e.targetNodeId !== nodeId) })
  }
  async function connect(targetId: string) {
    if (!workflow || !connectFromId || connectFromId === targetId) return
    const edge: WorkflowEdge = { id: `tmp-edge-${crypto.randomUUID()}`, sourceNodeId: connectFromId, targetNodeId: targetId, mapping: [{ from: 'payload', to: 'payload' }], condition: {} }
    await saveWorkflow({ ...workflow, edges: [...workflow.edges, edge] }); setConnectFromId(null)
  }
  async function moveNode(nodeId: string, x: number, y: number) {
    if (!workflow) return
    await saveWorkflow({ ...workflow, nodes: workflow.nodes.map((n) => n.id === nodeId ? { ...n, positionX: x, positionY: y } : n) })
  }
  async function updateNodeOverride(nodeId: string, configOverride: Record<string, unknown>) {
    if (!workflow) return
    await saveWorkflow({ ...workflow, nodes: workflow.nodes.map((n) => n.id === nodeId ? { ...n, configOverride } : n) })
  }
  async function runCurrentWorkflow() {
    if (!workflow) return
    try {
      setRunning(true)
      const parsed = parseJson<{ payload?: Record<string, unknown> }>(runPayload, '运行 payload')
      const result = await api.agent.runWorkflow(workflow.id, { payload: parsed.payload ?? parsed })
      setRunResult(result as unknown as Record<string, unknown>)
      setMessage('工作流执行完成')
    } catch (e) {
      setMessage(e instanceof Error ? e.message : '工作流执行失败')
    } finally { setRunning(false) }
  }
  async function updateEdgeMapping(edgeId: string, mapping: Record<string, unknown>[]) {
    if (!workflow) return
    await saveWorkflow({ ...workflow, edges: workflow.edges.map((e) => e.id === edgeId ? { ...e, mapping } : e) })
  }
  const validationIssues = useMemo(() => validateWorkflow(workflow, agentById), [workflow, agentById])
  const filteredAgents = useMemo(() => agents.filter((agent) => {
    const matchesQuery = `${agent.name} ${agent.role}`.toLowerCase().includes(agentQuery.trim().toLowerCase())
    const normalizedStatus = normalizeAgentStatus(agent.status)
    const matchesFilter = agentFilter === 'all' || normalizedStatus === agentFilter
    return matchesQuery && matchesFilter
  }), [agents, agentFilter, agentQuery])
  const agentValidation = useMemo(() => validateAgentDraft(draft), [draft])
  const configuredRequiredFields = useMemo(() => countConfiguredAgentFields(draft), [draft])
  async function publishCurrentWorkflow() {
    if (!workflow || validationIssues.length) return
    try {
      setPublishing(true)
      const published = await api.agent.publishWorkflow(workflow.id)
      setWorkflows((rows) => rows.map((w) => w.id === published.workflow.id ? published.workflow : w))
      setWorkflowVersions((rows) => [published.version, ...rows])
      setMessage(`工作流已发布为 v${published.version.version}`)
    } catch (e) {
      setMessage(e instanceof Error ? e.message : '工作流发布失败')
    } finally { setPublishing(false) }
  }

  return <div className="agent-studio">
    <header className="agent-console-titlebar">
      <div><h2>Agent Console</h2><p>管理 Agent 的模型、提示词、输入输出契约、权限边界与运行策略。</p></div>
      <div className="agent-console-title-actions">
        {workspace === 'agents' && <>
          <button className="btn secondary">导入模板</button>
          <button className="btn secondary" onClick={()=>setWorkspace('runs')}>运行测试</button>
          <button className="btn" disabled={saveState !== 'modified'} onClick={saveAgent}>{saveState === 'saving' ? 'Saving...' : saveState === 'saved' ? 'Saved' : 'Save Changes'}</button>
          <button className="btn" onClick={newAgent}>New Agent</button>
        </>}
      </div>
    </header>
    {message && <div className="agent-studio-message">{message}</div>}
    <nav className="agent-workspace-nav">
      <button className={workspace==='agents'?'active':''} onClick={()=>setWorkspace('agents')}><strong>Agents</strong><em>{agents.length}</em></button>
      <button className={workspace==='workflows'?'active':''} onClick={()=>setWorkspace('workflows')}><strong>Workflows</strong><em>{workflows.length}</em></button>
      <button className={workspace==='runs'?'active':''} onClick={()=>setWorkspace('runs')}><strong>Runs</strong><em>{runResult ? 1 : 0}</em></button>
    </nav>
    {workspace==='agents' && <section className="agent-workspace">
      <div className="agent-console-grid">
      <AgentSidebar agents={filteredAgents} selectedAgentId={selectedAgentId} query={agentQuery} filter={agentFilter} onQueryChange={setAgentQuery} onFilterChange={setAgentFilter} onSelect={selectAgent} onNewAgent={newAgent} />
      <section className="agent-editor">
        <AgentHeader draft={draft} editing={editing} saveState={saveState} lastSavedAt={lastSavedAt} onToggleEditing={()=>setEditing((v)=>!v)} onRun={()=>setWorkspace('runs')} onSave={saveAgent} />
        <div className="agent-editor-mode">
          <div>
            <strong>{editorMode==='guided'?'Guided':'Expert'}</strong>
            <span>{editorMode==='guided'?'仅展示必要字段，适合快速完成基础配置。':'展示高级模型、权限、运行策略和契约配置。'}</span>
          </div>
          <div><button className={editorMode==='guided'?'active':''} onClick={()=>setEditorMode('guided')}>Guided</button><button className={editorMode==='expert'?'active':''} onClick={()=>setEditorMode('expert')}>Expert</button></div>
        </div>
        <AgentConfigTabs step={step} onChange={setStep} />
        <div className="agent-config-body">
        {step===0 && <div className="agent-form-grid"><Field label="名称"><input disabled={!editing} value={draft.name} onChange={e=>update('name',e.target.value)} /></Field><Field label="角色"><input disabled={!editing} value={draft.role} onChange={e=>update('role',e.target.value)} /></Field><Field label="头像"><input disabled={!editing} value={draft.avatar} onChange={e=>update('avatar',e.target.value)} /></Field><Field label="自治级别"><select disabled={!editing} value={draft.autonomy} onChange={e=>update('autonomy',e.target.value)}><option>autonomous</option><option>supervised</option><option>human_gate</option></select></Field><Field label="描述"><textarea disabled={!editing} value={draft.description} onChange={e=>update('description',e.target.value)} /></Field><Field label="工作目标"><textarea disabled={!editing} value={draft.objective} onChange={e=>update('objective',e.target.value)} /></Field><Field label="下游交接"><textarea disabled={!editing} value={draft.downstreamHint} onChange={e=>update('downstreamHint',e.target.value)} /></Field></div>}
        {step===1 && <div className="agent-form-grid"><Field label="模型"><select disabled={!editing} value={String(draft.modelConfig.model ?? '')} onChange={e=>{const next={...draft.modelConfig,model:e.target.value}; update('modelConfig',next); updateJson('modelConfig',pretty(next))}}>{MODEL_OPTIONS.map(m=><option key={m}>{m}</option>)}</select></Field>{editorMode==='expert' && <JsonFieldArea disabled={!editing} label="模型配置 JSON" value={jsonDrafts.modelConfig} onChange={v=>updateJson('modelConfig',v)} />}<PromptEditor label="系统提示词" value={draft.systemPrompt} disabled={!editing} onChange={v=>update('systemPrompt',v)} /><PromptEditor label="用户提示词模板" value={draft.userPromptTemplate} disabled={!editing} onChange={v=>update('userPromptTemplate',v)} /></div>}
        {step===2 && (editorMode==='guided' ? <ContractEditor title="原始输入输出" inputLabel="原始输入" outputLabel="原始输出" input={draft.inputSchema} output={draft.outputSchema} disabled={!editing} onInputChange={schema=>{update('inputSchema',schema); updateJson('inputSchema',pretty(schema))}} onOutputChange={schema=>{update('outputSchema',schema); updateJson('outputSchema',pretty(schema))}} onExpert={()=>setEditorMode('expert')} /> : <div className="agent-json-grid"><JsonFieldArea disabled={!editing} label="原始输入 Schema" value={jsonDrafts.inputSchema} onChange={v=>updateJson('inputSchema',v)} /><JsonFieldArea disabled={!editing} label="原始输出 Schema" value={jsonDrafts.outputSchema} onChange={v=>updateJson('outputSchema',v)} /></div>)}
        {step===3 && (editorMode==='guided' ? <ContractEditor title="标准化结构" inputLabel="标准化输入" outputLabel="标准化输出" input={draft.normalizedInputSchema} output={draft.normalizedOutputSchema} disabled={!editing} onInputChange={schema=>{update('normalizedInputSchema',schema); updateJson('normalizedInputSchema',pretty(schema))}} onOutputChange={schema=>{update('normalizedOutputSchema',schema); updateJson('normalizedOutputSchema',pretty(schema))}} onExpert={()=>setEditorMode('expert')} /> : <div className="agent-json-grid"><JsonFieldArea disabled={!editing} label="标准化输入 Schema" value={jsonDrafts.normalizedInputSchema} onChange={v=>updateJson('normalizedInputSchema',v)} /><JsonFieldArea disabled={!editing} label="标准化输出 Schema" value={jsonDrafts.normalizedOutputSchema} onChange={v=>updateJson('normalizedOutputSchema',v)} /></div>)}
        {step===4 && (editorMode==='guided' ? <PolicySummary draft={draft} onExpert={()=>setEditorMode('expert')} /> : <div className="agent-json-grid"><JsonFieldArea disabled={!editing} label="输入映射" value={jsonDrafts.inputMapping} onChange={v=>updateJson('inputMapping',v)} /><JsonFieldArea disabled={!editing} label="输出映射" value={jsonDrafts.outputMapping} onChange={v=>updateJson('outputMapping',v)} /><JsonFieldArea disabled={!editing} label="工具权限" value={jsonDrafts.toolPolicy} onChange={v=>updateJson('toolPolicy',v)} /><JsonFieldArea disabled={!editing} label="约束" value={jsonDrafts.constraints} onChange={v=>updateJson('constraints',v)} /><JsonFieldArea disabled={!editing} label="运行策略" value={jsonDrafts.runtimePolicy} onChange={v=>updateJson('runtimePolicy',v)} /></div>)}
        </div>
      </section>
      <AgentInspector draft={draft} configuredRequiredFields={configuredRequiredFields} issues={agentValidation} saveState={saveState} runPayload={runPayload} runResult={runResult} onDryRun={()=>setWorkspace('runs')} />
      </div>
    </section>}
    {workspace==='workflows' && <section className="agent-workspace">
      <WorkspaceIntro eyebrow="Workflows" title="工作流编排与发布" description="这里管理的是链路草稿。节点可以引用 Agent 定义，也可以拥有自己的 override；发布后会生成不可变版本快照。" />
      <div className="workflow-studio"><div className="workflow-toolbar"><div><h3>工作流画布</h3><select value={selectedWorkflowId ?? ''} onChange={e=>setSelectedWorkflowId(e.target.value)}>{workflows.map(w=><option key={w.id} value={w.id}>{w.name}</option>)}</select>{workflow && <span className={`wf-status ${workflow.status}`}>{workflow.status === 'published' ? `已发布 v${workflow.version}` : `草稿 v${workflow.version}`}</span>}</div></div>
      {workflow && <WorkflowValidationStrip issues={validationIssues} onOpen={()=>{setSelectedNodeId(null);setSelectedEdgeId(null)}} />}
      {workflow && <div className="workflow-layout"><aside className="workflow-palette"><h4>节点库</h4><p>选择一个 Agent 添加到当前草稿。</p>{agents.map(a=><button key={a.id} onClick={()=>addNode(a.id)}><span>{a.avatar}</span><strong>{a.name}</strong><small>{a.role}</small></button>)}</aside><div className="workflow-canvas" ref={canvasRef}>
        <svg>{workflow.edges.map(e=>{const s=workflow.nodes.find(n=>n.id===e.sourceNodeId), t=workflow.nodes.find(n=>n.id===e.targetNodeId); return s&&t?<g key={e.id} className={selectedEdgeId===e.id?'selected':''} onClick={()=>{setSelectedEdgeId(e.id);setSelectedNodeId(null)}}><line className="edge-hit" x1={s.positionX+170} y1={s.positionY+35} x2={t.positionX} y2={t.positionY+35}/><line x1={s.positionX+170} y1={s.positionY+35} x2={t.positionX} y2={t.positionY+35}/></g>:null})}</svg>
        {workflow.nodes.map(n=><CanvasNode key={n.id} node={n} agent={agentById[n.agentDefinitionId]} selected={selectedNodeId===n.id} connecting={connectFromId===n.id} onSelect={()=>{setSelectedNodeId(n.id);setSelectedEdgeId(null); void connect(n.id)}} onStartConnect={()=>setConnectFromId(n.id)} onRemove={()=>void removeNode(n.id)} onMove={moveNode} />)}
      </div><aside className="workflow-inspector">
        {selectedEdge ? <EdgeInspector edge={selectedEdge} source={agentById[workflow.nodes.find(n=>n.id===selectedEdge.sourceNodeId)?.agentDefinitionId ?? '']} target={agentById[workflow.nodes.find(n=>n.id===selectedEdge.targetNodeId)?.agentDefinitionId ?? '']} onSave={m=>void updateEdgeMapping(selectedEdge.id,m)} /> : selectedNode ? <NodeInspector node={selectedNode} agent={agentById[selectedNode.agentDefinitionId]} onSave={o=>void updateNodeOverride(selectedNode.id,o)} /> : <ValidationPanel issues={validationIssues} />}
      </aside></div>}
      {workflow && <WorkflowPublishPanel versions={workflowVersions} issues={validationIssues} publishing={publishing} onPublish={()=>void publishCurrentWorkflow()} />}
      </div>
    </section>}
    {workspace==='runs' && <section className="agent-workspace">
      <WorkspaceIntro eyebrow="Runs" title="运行调试" description="这里查看一次执行，而不是编辑配置。先选择工作流，再输入 payload 进行调试运行。" />
      <div className="run-workspace-head">
        <div><span>当前工作流</span><strong>{workflow?.name ?? '未选择'}</strong></div>
        <select value={selectedWorkflowId ?? ''} onChange={e=>setSelectedWorkflowId(e.target.value)}>{workflows.map(w=><option key={w.id} value={w.id}>{w.name}</option>)}</select>
      </div>
      {workflow && <WorkflowRunPanel payload={runPayload} onPayloadChange={setRunPayload} running={running} onRun={()=>void runCurrentWorkflow()} result={runResult} />}
    </section>}
    {showNewAgent && <NewAgentModal agents={agents} role={newAgentRole} templateId={newAgentTemplateId} name={newAgentName} onRoleChange={setNewAgentRole} onTemplateChange={setNewAgentTemplateId} onNameChange={setNewAgentName} onClose={()=>setShowNewAgent(false)} onCreate={createAgentDraft} />}
  </div>
}
function WorkspaceIntro({eyebrow,title,description}:{eyebrow:string;title:string;description:string}){return <header className="agent-workspace-intro"><span>{eyebrow}</span><h3>{title}</h3><p>{description}</p></header>}
function AgentSidebar({agents,selectedAgentId,query,filter,onQueryChange,onFilterChange,onSelect,onNewAgent}:{agents:AgentDefinition[];selectedAgentId:string|null;query:string;filter:AgentFilter;onQueryChange:(value:string)=>void;onFilterChange:(value:AgentFilter)=>void;onSelect:(agent:AgentDefinition)=>void;onNewAgent:()=>void}) {
  return <aside className="agent-library">
    <div className="agent-library-head"><h3>Agents</h3><button onClick={onNewAgent}>＋</button></div>
    <input className="agent-search" placeholder="Search agents" value={query} onChange={e=>onQueryChange(e.target.value)} />
    <div className="agent-filter-row">{(['all','active','draft'] as AgentFilter[]).map((item)=><button key={item} className={filter===item?'active':''} onClick={()=>onFilterChange(item)}>{capitalize(item)}</button>)}</div>
    <div className="agent-list">
      {agents.map((agent)=><button key={agent.id} className={agent.id===selectedAgentId?'active':''} onClick={()=>onSelect(agent)}>
        <span>{agent.avatar}</span>
        <strong>{agent.name}</strong>
        <small>{agent.role}</small>
        <StatusBadge status={normalizeAgentStatus(agent.status)} />
        <em>{agent.status === 'active' ? 'Ready' : agent.status}</em>
      </button>)}
      {agents.length===0 && <p className="agent-empty">没有匹配的 Agent。</p>}
    </div>
  </aside>
}
function AgentHeader({draft,editing,saveState,lastSavedAt,onToggleEditing,onRun,onSave}:{draft:Draft;editing:boolean;saveState:SaveState;lastSavedAt:string|null;onToggleEditing:()=>void;onRun:()=>void;onSave:()=>void}) {
  return <header className="agent-config-header">
    <div>
      <h3>{draft.name || 'Untitled Agent'}</h3>
      <div><code>{draft.role || 'unassigned'}</code><span>{draft.autonomy}</span><StatusBadge status={normalizeAgentStatus(draft.status)} /><em>{saveState === 'modified' ? 'Modified' : saveState === 'saving' ? 'Saving...' : lastSavedAt ? 'Saved just now' : 'Saved'}</em></div>
    </div>
    <div>
      <button className="btn secondary" onClick={onToggleEditing}>{editing ? 'View Mode' : 'Edit Mode'}</button>
      <button className="btn secondary" onClick={onRun}>Run Test</button>
      <button className="btn secondary">Duplicate</button>
      <button className="btn" disabled={saveState !== 'modified'} onClick={onSave}>{saveState === 'saving' ? 'Saving...' : 'Save Changes'}</button>
    </div>
  </header>
}
function AgentConfigTabs({step,onChange}:{step:number;onChange:(step:number)=>void}) {
  return <nav className="agent-config-tabs">{STEPS.map((item,index)=><button key={item} className={index===step?'active':''} onClick={()=>onChange(index)}>{item}</button>)}</nav>
}
function AgentInspector({draft,configuredRequiredFields,issues,saveState,runPayload,runResult,onDryRun}:{draft:Draft;configuredRequiredFields:number;issues:AgentIssue[];saveState:SaveState;runPayload:string;runResult:Record<string,unknown>|null;onDryRun:()=>void}) {
  const typed = runResult as any
  return <aside className="agent-inspector">
    <section>
      <h3>Configuration Status</h3>
      <dl>
        <div><dt>Required fields</dt><dd>{configuredRequiredFields} / 10</dd></div>
        <div><dt>Prompt configured</dt><dd>{draft.systemPrompt || draft.userPromptTemplate ? 'yes' : 'no'}</dd></div>
        <div><dt>IO contract</dt><dd>{issues.some((issue)=>issue.key==='io') ? 'invalid' : 'valid'}</dd></div>
        <div><dt>Permission scope</dt><dd>{draft.autonomy}</dd></div>
      </dl>
    </section>
    <section>
      <h3>Validation</h3>
      <ul>{issues.map((issue)=><li key={issue.label} className={issue.level}>{issue.label}</li>)}</ul>
    </section>
    <section>
      <h3>Test Run Preview</h3>
      <label>Input sample</label>
      <pre>{runPayload}</pre>
      <label>Expected output</label>
      <pre>{pretty(draft.normalizedOutputSchema)}</pre>
      <button onClick={onDryRun}>Run dry test</button>
      <small>{runResult ? `最近一次运行：${String(typed.result?.current?.status ?? 'completed')}` : `当前状态：${saveState === 'modified' ? '保存后可运行测试' : '尚未运行'}`}</small>
    </section>
  </aside>
}
function StatusBadge({status}:{status:string}){return <span className={`agent-status-badge ${status}`}>{capitalize(status)}</span>}
function NewAgentModal({agents,role,templateId,name,onRoleChange,onTemplateChange,onNameChange,onClose,onCreate}:{agents:AgentDefinition[];role:string;templateId:string;name:string;onRoleChange:(value:string)=>void;onTemplateChange:(value:string)=>void;onNameChange:(value:string)=>void;onClose:()=>void;onCreate:()=>void}) {
  return <div className="agent-modal-backdrop">
    <section className="agent-modal">
      <header><div><h3>New Agent</h3><p>基于模板创建 Agent 草稿，再进入配置台完善细节。</p></div><button onClick={onClose}>×</button></header>
      <Field label="Agent 类型"><select value={role} onChange={e=>onRoleChange(e.target.value)}>{['backtest','execution','explain','portfolio'].map((item)=><option key={item}>{item}</option>)}</select></Field>
      <Field label="模板"><select value={templateId} onChange={e=>onTemplateChange(e.target.value)}><option value="">空白模板</option>{agents.map((agent)=><option key={agent.id} value={agent.id}>{agent.name}</option>)}</select></Field>
      <Field label="名称"><input value={name} onChange={e=>onNameChange(e.target.value)} placeholder={`${capitalize(role)} Agent`} /></Field>
      <footer><button className="btn secondary" onClick={onClose}>取消</button><button className="btn" onClick={onCreate}>创建草稿</button></footer>
    </section>
  </div>
}
function Field({label,children}:{label:string;children:ReactNode}){return <label className="agent-field"><span>{label}</span>{children}</label>}
function JsonFieldArea({label,value,onChange,disabled}:{label:string;value:string;onChange:(v:string)=>void;disabled:boolean}){return <Field label={label}><textarea className="json" disabled={disabled} value={value} onChange={e=>onChange(e.target.value)} /></Field>}
function PromptEditor({label,value,onChange,disabled}:{label:string;value:string;onChange:(v:string)=>void;disabled:boolean}) {
  const variables = extractPromptVariables(value)
  const preview = renderPromptPreview(value, variables)
  return <section className="prompt-editor">
    <Field label={label}><textarea disabled={disabled} value={value} onChange={e=>onChange(e.target.value)} /></Field>
    <div className="prompt-editor-meta">
      <div><span>变量</span>{variables.length===0?<small>暂未识别到变量</small>:variables.map(v=><code key={v}>{`{{${v}}}`}</code>)}</div>
      <div><span>模板预览</span><pre>{preview || '输入模板后，这里会展示示例渲染结果。'}</pre></div>
    </div>
  </section>
}
function ContractEditor({title,inputLabel,outputLabel,input,output,disabled,onInputChange,onOutputChange,onExpert}:{title:string;inputLabel:string;outputLabel:string;input:Record<string,unknown>;output:Record<string,unknown>;disabled:boolean;onInputChange:(schema:Record<string,unknown>)=>void;onOutputChange:(schema:Record<string,unknown>)=>void;onExpert:()=>void}){return <div className="contract-editor"><div className="contract-editor-head"><div><h4>{title}</h4><p>引导模式下直接维护字段；复杂约束仍可切回专家 JSON。</p></div><button onClick={onExpert}>进入专家模式编辑 JSON</button></div><div className="contract-editor-grid"><SchemaEditor title={inputLabel} schema={input} disabled={disabled} onChange={onInputChange} /><SchemaEditor title={outputLabel} schema={output} disabled={disabled} onChange={onOutputChange} /></div></div>}
function SchemaEditor({title,schema,disabled,onChange}:{title:string;schema:Record<string,unknown>;disabled:boolean;onChange:(schema:Record<string,unknown>)=>void}) {
  const properties = ((schema.properties ?? {}) as Record<string, any>)
  const required = new Set(requiredFields(schema))
  const rows = Object.entries(properties)
  const mutate = (name:string, patch:Record<string,unknown>) => onChange({...schema, type:'object', properties:{...properties,[name]:{...(properties[name] ?? {}),...patch}}, required:Array.from(required)})
  const rename = (from:string, to:string) => {
    if(!to || from===to || properties[to]) return
    const nextProps = {...properties}; nextProps[to] = nextProps[from]; delete nextProps[from]
    const nextRequired = Array.from(required).map(item=>item===from?to:item)
    onChange({...schema, type:'object', properties:nextProps, required:nextRequired})
  }
  const toggleRequired = (name:string) => {
    const next = new Set(required); next.has(name)?next.delete(name):next.add(name)
    onChange({...schema, type:'object', properties, required:Array.from(next)})
  }
  const remove = (name:string) => {
    const nextProps = {...properties}; delete nextProps[name]
    onChange({...schema, type:'object', properties:nextProps, required:Array.from(required).filter(item=>item!==name)})
  }
  const add = () => {
    const base='field'
    let i=rows.length+1
    let name=`${base}_${i}`
    while(properties[name]) { i += 1; name=`${base}_${i}` }
    onChange({...schema, type:'object', properties:{...properties,[name]:{type:'string',description:''}}, required:Array.from(required)})
  }
  return <section className="schema-editor"><header><div><strong>{title}</strong><small>{rows.length} 个字段 · {required.size} 个必填</small></div><button disabled={disabled} onClick={add}>新增字段</button></header>{rows.length===0?<p className="schema-empty">暂无字段，先补齐核心输入输出，后续连线校验才会更可靠。</p>:<div className="schema-table">{rows.map(([name,meta])=><div key={name} className="schema-row"><input disabled={disabled} defaultValue={name} onBlur={e=>rename(name,e.target.value.trim())} /><select disabled={disabled} value={String(meta.type ?? 'string')} onChange={e=>mutate(name,{type:e.target.value})}><option>string</option><option>number</option><option>integer</option><option>boolean</option><option>object</option><option>array</option></select><input disabled={disabled} value={String(meta.description ?? '')} placeholder="字段说明" onChange={e=>mutate(name,{description:e.target.value})} /><label><input disabled={disabled} type="checkbox" checked={required.has(name)} onChange={()=>toggleRequired(name)} />必填</label><button disabled={disabled} onClick={()=>remove(name)}>删除</button></div>)}</div>}</section>
}
function PolicySummary({draft,onExpert}:{draft:Draft;onExpert:()=>void}){return <div className="agent-summary-panel"><div><h4>映射与约束</h4><p>保留完整配置，但默认先展示摘要，避免第一次编辑就陷入底层细节。</p></div><div className="agent-summary-grid"><SummaryCard label="输入映射" value={draft.inputMapping.length} detail="字段映射规则" /><SummaryCard label="输出映射" value={draft.outputMapping.length} detail="字段映射规则" /><SummaryCard label="工具权限" value={draft.toolPolicy.length} detail="已配置策略" /><SummaryCard label="约束" value={draft.constraints.length} detail={`超时 ${String(draft.runtimePolicy.timeoutSeconds ?? '—')}s`} /></div><button onClick={onExpert}>进入专家模式编辑完整策略</button></div>}
function SummaryCard({label,value,detail}:{label:string;value:number;detail:string}){return <article className="agent-summary-card"><span>{label}</span><strong>{value}</strong><small>{detail}</small></article>}
function CanvasNode({node,agent,selected,connecting,onSelect,onStartConnect,onRemove,onMove}:{node:WorkflowNode;agent?:AgentDefinition;selected:boolean;connecting:boolean;onSelect:()=>void;onStartConnect:()=>void;onRemove:()=>void;onMove:(id:string,x:number,y:number)=>void}){
  return <div className={`workflow-node ${selected?'selected':''} ${connecting?'connecting':''}`} style={{left:node.positionX,top:node.positionY}} onMouseDown={(e)=>{if((e.target as HTMLElement).closest('button'))return; const sx=e.clientX, sy=e.clientY, ox=node.positionX, oy=node.positionY; const move=(ev:MouseEvent)=>{(e.currentTarget as HTMLDivElement).style.left=`${ox+ev.clientX-sx}px`; (e.currentTarget as HTMLDivElement).style.top=`${oy+ev.clientY-sy}px`}; const up=(ev:MouseEvent)=>{window.removeEventListener('mousemove',move);window.removeEventListener('mouseup',up);onMove(node.id,ox+ev.clientX-sx,oy+ev.clientY-sy)}; window.addEventListener('mousemove',move);window.addEventListener('mouseup',up)}} onClick={onSelect}><strong>{agent?.avatar} {node.label ?? agent?.name}</strong><small>{agent?.role}</small><div><button onClick={(e)=>{e.stopPropagation();onStartConnect()}}>连线</button><button onClick={(e)=>{e.stopPropagation();onRemove()}}>删除</button></div></div>
}

function schemaFields(schema: Record<string, unknown>){const props=(schema.properties ?? {}) as Record<string, unknown>; return Object.keys(props)}
function requiredFields(schema: Record<string, unknown>){return Array.isArray(schema.required)?schema.required.map(String):[]}
type AgentIssue = { key: 'model' | 'prompt' | 'io' | 'mapping' | 'risk'; label: string; level: 'info' | 'warning' | 'error' }
function normalizeAgentStatus(status:string){return status === 'active' ? 'active' : status === 'disabled' ? 'disabled' : 'draft'}
function capitalize(value:string){return value ? value[0].toUpperCase() + value.slice(1) : value}
function countConfiguredAgentFields(draft:Draft){
  return [
    draft.name, draft.role, draft.avatar, draft.description, draft.objective, draft.downstreamHint,
    draft.modelConfig.provider, draft.modelConfig.model, draft.systemPrompt || draft.userPromptTemplate,
    schemaFields(draft.normalizedOutputSchema).length > 0,
  ].filter(Boolean).length
}
function validateAgentDraft(draft:Draft):AgentIssue[]{
  const issues:AgentIssue[]=[]
  if(!draft.modelConfig.provider || !draft.modelConfig.model) issues.push({key:'model',label:'Missing model provider',level:'error'})
  if(!draft.systemPrompt && !draft.userPromptTemplate) issues.push({key:'prompt',label:'Prompt not configured',level:'warning'})
  if(schemaFields(draft.inputSchema).length===0 || schemaFields(draft.outputSchema).length===0) issues.push({key:'io',label:'Raw IO contract incomplete',level:'error'})
  if(schemaFields(draft.normalizedOutputSchema).length===0) issues.push({key:'mapping',label:'Output schema not mapped',level:'warning'})
  if(draft.constraints.length===0) issues.push({key:'risk',label:'Risk policy not attached',level:'info'})
  return issues
}
function extractPromptVariables(value:string){return Array.from(new Set(Array.from(value.matchAll(/\{\{\s*([a-zA-Z0-9_.-]+)\s*\}\}/g)).map(m=>m[1])))}
function renderPromptPreview(value:string,variables:string[]){return variables.reduce((acc,v)=>acc.replaceAll(new RegExp(`\\{\\{\\s*${escapeRegExp(v)}\\s*\\}\\}`,'g'),samplePromptValue(v)),value)}
function samplePromptValue(name: string) {
  const n = name.toLowerCase()
  if (n.includes('symbol')) return '000001.SZ'
  if (n.includes('risk')) return 'medium'
  if (n.includes('trace')) return ''
  return ''
}
function escapeRegExp(value:string){return value.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')}
function validateWorkflow(workflow: AgentWorkflow | null, agentById: Record<string, AgentDefinition>){
 if(!workflow) return [] as string[]
 const issues:string[]=[]
 for(const edge of workflow.edges){
  const sourceNode=workflow.nodes.find(n=>n.id===edge.sourceNodeId), targetNode=workflow.nodes.find(n=>n.id===edge.targetNodeId)
  const source=sourceNode?agentById[sourceNode.agentDefinitionId]:undefined, target=targetNode?agentById[targetNode.agentDefinitionId]:undefined
  if(!source || !target){issues.push(`边 ${edge.id} 存在缺失节点`); continue}
  const sourceFields=new Set(schemaFields(source.normalizedOutputSchema)); const targetRequired=requiredFields(target.normalizedInputSchema).filter(f=>f!=='traceId')
  const mappedTo=new Set(edge.mapping.map(m=>String(m.to ?? ''))); const mappedFrom=edge.mapping.map(m=>String(m.from ?? ''))
  for(const f of mappedFrom){ if(f && !sourceFields.has(f)) issues.push(`${source.name} → ${target.name}: 上游字段 ${f} 不存在`) }
  for(const f of targetRequired){ if(!mappedTo.has(f)) issues.push(`${source.name} → ${target.name}: 下游必填字段 ${f} 未映射`) }
 }
 return issues
}
function NodeInspector({node,agent,onSave}:{node:WorkflowNode;agent?:AgentDefinition;onSave:(o:Record<string,unknown>)=>void}){ const [overrideText,setOverrideText]=useState(()=>pretty(node.configOverride)); useEffect(()=>setOverrideText(pretty(node.configOverride)),[node]); if(!agent) return <p className="wf-muted">未找到节点 Agent。</p>; return <div className="workflow-panel"><h4>{agent.name}</h4><small>{agent.role}</small><section><label>标准化输入</label><pre>{pretty(agent.normalizedInputSchema)}</pre></section><section><label>标准化输出</label><pre>{pretty(agent.normalizedOutputSchema)}</pre></section><section><label>节点 Override</label><textarea className="wf-override" value={overrideText} onChange={e=>setOverrideText(e.target.value)} /><button onClick={()=>onSave(parseJson<Record<string,unknown>>(overrideText,'节点 override'))}>保存 Override</button></section></div> }
function ValidationPanel({issues}:{issues:string[]}){return <div className="workflow-panel"><h4>链路校验</h4>{issues.length===0?<p className="wf-ok">当前链路契约可用</p>:<ul className="wf-issues">{issues.map(i=><li key={i}>{i}</li>)}</ul>}</div>}
function WorkflowValidationStrip({issues,onOpen}:{issues:string[];onOpen:()=>void}){return <button className={`workflow-validation-strip ${issues.length?'invalid':'valid'}`} onClick={onOpen}><strong>{issues.length===0?'当前链路可发布':'当前链路存在问题'}</strong><span>{issues.length===0?'契约校验通过，可继续发布。':`${issues.length} 项问题需要处理，点击查看详情。`}</span></button>}
function WorkflowPublishPanel({versions,issues,publishing,onPublish}:{versions:WorkflowVersion[];issues:string[];publishing:boolean;onPublish:()=>void}){return <div className="workflow-publish"><div><h4>发布版本</h4><p>发布会冻结当前工作流、节点 override 和 Agent 定义快照。</p></div><div className="workflow-version-list">{versions.length===0?<span>暂无已发布版本</span>:versions.map(v=><span key={v.id}>v{v.version}</span>)}</div><button disabled={publishing||issues.length>0} onClick={onPublish}>{publishing?'发布中…':'发布当前草稿'}</button></div>}
function EdgeInspector({edge,source,target,onSave}:{edge:WorkflowEdge;source?:AgentDefinition;target?:AgentDefinition;onSave:(m:Record<string,unknown>[])=>void}){const [rows,setRows]=useState(()=>edge.mapping.map(m=>({from:String(m.from??''),to:String(m.to??'')}))); useEffect(()=>setRows(edge.mapping.map(m=>({from:String(m.from??''),to:String(m.to??'')}))),[edge]); return <div className="workflow-panel"><h4>边映射</h4><p>{source?.name ?? '未知'} → {target?.name ?? '未知'}</p><div className="edge-map-list">{rows.map((r,i)=><div key={i}><input list={`src-${edge.id}`} value={r.from} onChange={e=>setRows(v=>v.map((x,idx)=>idx===i?{...x,from:e.target.value}:x))}/><span>→</span><input list={`dst-${edge.id}`} value={r.to} onChange={e=>setRows(v=>v.map((x,idx)=>idx===i?{...x,to:e.target.value}:x))}/><button onClick={()=>setRows(v=>v.filter((_,idx)=>idx!==i))}>删</button></div>)}</div><datalist id={`src-${edge.id}`}>{schemaFields(source?.normalizedOutputSchema ?? {}).map(f=><option key={f} value={f}/>)}</datalist><datalist id={`dst-${edge.id}`}>{schemaFields(target?.normalizedInputSchema ?? {}).map(f=><option key={f} value={f}/>)}</datalist><div className="edge-actions"><button onClick={()=>setRows(v=>[...v,{from:'',to:''}])}>新增映射</button><button onClick={()=>onSave(rows)}>保存映射</button></div></div>}

function WorkflowRunPanel({payload,onPayloadChange,running,onRun,result}:{payload:string;onPayloadChange:(v:string)=>void;running:boolean;onRun:()=>void;result:Record<string,unknown>|null}){const typed=result as any; const history=typed?.result?.history ?? []; return <div className="workflow-run"><div><h4>运行调试</h4><textarea value={payload} onChange={e=>onPayloadChange(e.target.value)} /><button onClick={onRun} disabled={running}>{running?'执行中…':'运行当前工作流'}</button></div><div><h4>执行结果</h4>{!result?<p className="wf-muted">尚未运行</p>:<><RunSummary traceId={String(typed.traceId ?? '—')} steps={history.length} current={typed.result?.current ?? {}} /><RunTimeline history={history} /></>}</div></div>}
function RunSummary({traceId,steps,current}:{traceId:string;steps:number;current:Record<string,unknown>}){return <div className="run-summary"><span>Trace</span><strong>{traceId}</strong><span>节点数</span><strong>{steps}</strong><span>最终状态</span><strong>{String(current.status ?? '—')}</strong></div>}
function RunTimeline({history}:{history:any[]}){return <ol className="run-timeline">{history.map((h:any,i:number)=><li key={i}><div><span>{i+1}</span><strong>{h.agent}</strong></div><code>{pretty(h.result)}</code></li>)}</ol>}
