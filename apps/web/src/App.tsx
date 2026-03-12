import { useEffect, useMemo, useState } from 'react'
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Badge, Button, Card, EmptyState, ErrorState, InlineNotice, Input, LoadingState, Modal, SectionTitle, SkeletonBlock } from './components/ui'
import { apiFetch, apiToken, cn } from './lib/utils'
import type {
  ActionExecuteIn,
  ActionExecuteOut,
  Client,
  HealthFreshness,
  Link,
  NotificationItem,
  Overview,
  ServerStatus,
  SessionDrilldown,
  SessionItem,
  TimelineEvent
} from './types/api'

type TabKey = 'dashboard' | 'links' | 'clients' | 'sessions' | 'settings'
type EventItem = { id: number; title: string; message: string; level: string; created_at: string }
type LogItem = { id: number; action: string; status: string; created_at: string }
type PushNotice = { id: number; title: string; message: string; tone: 'info' | 'warning' }

type SavedView = { name: string; query: string; status: string }

const statusLabel: Record<string, string> = { active: 'Активен', idle: 'Неактивен', disabled: 'Отключен', running: 'Работает', closed: 'Завершена' }
const dateTime = new Intl.DateTimeFormat('ru-RU', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })

function formatTraffic(value: number) { return `${value.toFixed(1)} GB` }
function formatDate(value?: string | null) { if (!value) return '—'; return dateTime.format(new Date(value)) }
function toneByStatus(status?: string) { if (status === 'active' || status === 'running') return 'success'; if (status === 'disabled') return 'danger'; if (status === 'idle' || status === 'closed') return 'default'; return 'info' }

const defaults: Record<TabKey, SavedView[]> = {
  dashboard: [],
  links: [{ name: 'Отключённые', query: '', status: 'disabled' }, { name: 'Активные', query: '', status: 'active' }],
  clients: [{ name: 'Подозрительные', query: 'suspicious', status: 'all' }],
  sessions: [{ name: 'Активные сейчас', query: '', status: 'active' }, { name: 'Завершённые', query: '', status: 'closed' }],
  settings: []
}

function loadViews(tab: TabKey): SavedView[] {
  const raw = localStorage.getItem(`views:${tab}`)
  if (!raw) return defaults[tab]
  try { return JSON.parse(raw) as SavedView[] } catch { return defaults[tab] }
}

function saveViews(tab: TabKey, views: SavedView[]) {
  localStorage.setItem(`views:${tab}`, JSON.stringify(views))
}

export function App() {
  const [tab, setTab] = useState<TabKey>('dashboard')
  const [overview, setOverview] = useState<Overview | null>(null)
  const [links, setLinks] = useState<Link[]>([])
  const [clients, setClients] = useState<Client[]>([])
  const [sessions, setSessions] = useState<SessionItem[]>([])
  const [server, setServer] = useState<ServerStatus | null>(null)
  const [events, setEvents] = useState<EventItem[]>([])
  const [logs, setLogs] = useState<LogItem[]>([])
  const [notifications, setNotifications] = useState<NotificationItem[]>([])
  const [health, setHealth] = useState<HealthFreshness | null>(null)
  const [sseState, setSseState] = useState<'connected' | 'disconnected'>('disconnected')
  const [lastRefreshAt, setLastRefreshAt] = useState<string | null>(null)

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [pushEnabled, setPushEnabled] = useState(true)
  const [pushNotices, setPushNotices] = useState<PushNotice[]>([])
  const [period, setPeriod] = useState<'24h' | '7d'>('24h')
  const [openCreate, setOpenCreate] = useState(false)
  const [openNotifications, setOpenNotifications] = useState(false)

  const [openAction, setOpenAction] = useState(false)
  const [actionPayload, setActionPayload] = useState<ActionExecuteIn | null>(null)
  const [actionReason, setActionReason] = useState('')
  const [actionRunning, setActionRunning] = useState(false)

  const [selectedSessionId, setSelectedSessionId] = useState<number | null>(null)
  const [sessionDrilldown, setSessionDrilldown] = useState<SessionDrilldown | null>(null)
  const [sessionTimeline, setSessionTimeline] = useState<TimelineEvent[]>([])
  const [sessionDrilldownLoading, setSessionDrilldownLoading] = useState(false)

  const [savedViews, setSavedViews] = useState<SavedView[]>(() => loadViews(tab))

  async function load() {
    setLoading(true)
    setError(null)
    try {
      const [ov, ls, cs, ss, sv, ev, lg, nt, hl] = await Promise.all([
        apiFetch<Overview>('/api/dashboard/overview'),
        apiFetch<Link[]>('/api/links'),
        apiFetch<Client[]>('/api/clients'),
        apiFetch<SessionItem[]>('/api/sessions'),
        apiFetch<ServerStatus>('/api/server/status'),
        apiFetch<EventItem[]>('/api/events'),
        apiFetch<LogItem[]>('/api/activity-log'),
        apiFetch<NotificationItem[]>('/api/notifications'),
        apiFetch<HealthFreshness>('/api/system/health')
      ])
      setOverview(ov); setLinks(ls); setClients(cs); setSessions(ss); setServer(sv); setEvents(ev); setLogs(lg); setNotifications(nt); setHealth(hl)
      setLastRefreshAt(new Date().toISOString())
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    setSavedViews(loadViews(tab))
  }, [tab])

  useEffect(() => {
    load()
    const base = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
    const src = new EventSource(`${base}/api/events/stream?token=${apiToken}`)
    src.onopen = () => setSseState('connected')
    src.onmessage = (event) => {
      if (!pushEnabled) return
      try {
        const payload = JSON.parse(event.data) as { kind?: string; title?: string; message?: string; type?: string; entity_type?: string; entity_id?: string }
        if (payload.kind === 'notification' && payload.title && payload.message) {
          const tone: PushNotice['tone'] = payload.type === 'warning' ? 'warning' : 'info'
          const incomingNotification: NotificationItem = {
            id: Date.now(),
            severity: payload.type ?? 'info',
            title: payload.title,
            message: payload.message,
            entity_type: payload.entity_type ?? null,
            entity_id: payload.entity_id ?? null,
            is_read: false,
            created_at: new Date().toISOString()
          }
          const incomingPush: PushNotice = { id: Date.now(), title: payload.title, message: payload.message, tone }
          setPushNotices((prev) => [incomingPush, ...prev].slice(0, 4))
          setNotifications((prev) => [incomingNotification, ...prev])
          setLastRefreshAt(new Date().toISOString())
        }
      } catch {}
    }
    src.onerror = () => {
      setSseState('disconnected')
      src.close()
    }
    return () => src.close()
  }, [pushEnabled])

  useEffect(() => { if (!notice) return; const t = setTimeout(() => setNotice(null), 2500); return () => clearTimeout(t) }, [notice])
  useEffect(() => { if (!pushNotices.length) return; const t = setTimeout(() => setPushNotices((prev) => prev.slice(0, -1)), 6000); return () => clearTimeout(t) }, [pushNotices])

  const chartData = useMemo(() => (period === '24h' ? overview?.chart_24h ?? [] : overview?.chart_7d ?? []), [period, overview])

  const freshnessState = useMemo(() => {
    if (!health) return { tone: 'warn' as const, text: 'Нет данных состояния' }
    if (sseState === 'disconnected') return { tone: 'danger' as const, text: 'Live stream отключён' }
    if (health.provider_status !== 'healthy' || health.backend_status !== 'ok') return { tone: 'warn' as const, text: 'Degraded состояние данных' }
    if (health.data_freshness_sec > 120) return { tone: 'warn' as const, text: 'Данные устарели' }
    return { tone: 'info' as const, text: 'Данные актуальны' }
  }, [health, sseState])

  function openActionCenter(payload: ActionExecuteIn) {
    setActionPayload(payload)
    setActionReason('')
    setOpenAction(true)
  }

  async function runAction() {
    if (!actionPayload) return
    setActionRunning(true)
    try {
      const result = await apiFetch<ActionExecuteOut>('/api/actions/execute', {
        method: 'POST',
        body: JSON.stringify({ ...actionPayload, reason: actionReason || undefined })
      })
      setNotice(`Успешно: ${result.result}`)
      setOpenAction(false)
      await load()
    } catch (e) {
      setNotice(`Ошибка: ${(e as Error).message}`)
    } finally {
      setActionRunning(false)
    }
  }

  async function openSession(id: number) {
    setSelectedSessionId(id)
    setSessionDrilldownLoading(true)
    try {
      const [drilldown, timeline] = await Promise.all([
        apiFetch<SessionDrilldown>(`/api/sessions/${id}/drilldown`),
        apiFetch<TimelineEvent[]>(`/api/timeline/sessions/${id}`)
      ])
      setSessionDrilldown(drilldown)
      setSessionTimeline(timeline)
    } catch {
      setSessionDrilldown(null)
      setSessionTimeline([])
    } finally {
      setSessionDrilldownLoading(false)
    }
  }

  function addSavedView(view: SavedView) {
    const updated = [view, ...savedViews]
    setSavedViews(updated)
    saveViews(tab, updated)
    setNotice('Представление сохранено')
  }

  return (
    <div className="min-h-screen bg-bg p-4 font-['Inter'] text-slate-100 md:p-6">
      <div className="mx-auto max-w-7xl space-y-5">
        <header className="space-y-3 rounded-2xl border border-border bg-panel p-4 shadow-soft">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div><h1 className="text-xl font-semibold md:text-2xl">Панель управления Xray / VLESS</h1><p className="text-sm text-muted">Финальная полировка UX Version 2</p></div>
            <nav className="flex flex-wrap gap-2">
              {([['dashboard','Дашборд'],['links','VLESS ссылки'],['clients','Клиенты'],['sessions','Сессии'],['settings','Настройки']] as const).map(([k,label]) => <Button key={k} variant={tab===k?'primary':'secondary'} onClick={() => setTab(k)}>{label}</Button>)}
            </nav>
          </div>
          <div className="grid gap-2 rounded-xl border border-border bg-bg p-3 md:grid-cols-5">
            <div className="md:col-span-2"><span className="text-xs text-muted">Health/Freshness</span><p className="text-sm"><Badge tone={freshnessState.tone}>{freshnessState.text}</Badge></p></div>
            <div><span className="text-xs text-muted">Xray/Provider</span><p className="text-sm">{health?.server_status ?? 'unknown'} / {health?.provider_status ?? 'unknown'}</p></div>
            <div><span className="text-xs text-muted">SSE</span><p className="text-sm"><Badge tone={sseState === 'connected' ? 'success' : 'danger'}>{sseState === 'connected' ? 'connected' : 'disconnected'}</Badge></p></div>
            <div><span className="text-xs text-muted">Последнее обновление</span><p className="text-sm">{formatDate(lastRefreshAt)}</p></div>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button variant="ghost" onClick={() => setPushEnabled((v)=>!v)}>{pushEnabled ? 'Push: Вкл':'Push: Выкл'}</Button>
            <Button variant="secondary" onClick={() => setOpenNotifications(true)}>Уведомления ({notifications.filter(n=>!n.is_read).length})</Button>
            <Button variant="secondary" onClick={() => openActionCenter({ action: 'reload', target_type: 'server' })}>Центр действий: Reload</Button>
            <Button variant="danger" onClick={() => openActionCenter({ action: 'restart', target_type: 'server' })}>Центр действий: Restart</Button>
          </div>
        </header>

        {notice && <InlineNotice tone={notice.startsWith('Ошибка') ? 'danger' : 'info'} text={notice} />}
        {error && <ErrorState message={error} onRetry={load} />}
        {loading && <SkeletonBlock rows={6} />}

        {!loading && !error && overview && (
          <>
            {tab === 'dashboard' && (
              <div className="grid gap-3 lg:grid-cols-4">
                <Card><SectionTitle title="Ссылки" /><p className="text-2xl font-semibold">{overview.total_links}</p></Card>
                <Card><SectionTitle title="Активные подключения" /><p className="text-2xl font-semibold">{overview.active_connections}</p></Card>
                <Card><SectionTitle title="Трафик 24ч" /><p className="text-2xl font-semibold">{overview.traffic_24h_gb.toFixed(1)} GB</p></Card>
                <Card><SectionTitle title="Сервер" /><Badge tone={toneByStatus(overview.server_status) as any}>{statusLabel[overview.server_status] ?? overview.server_status}</Badge></Card>
                <Card className="lg:col-span-4">
                  <div className="mb-2 flex items-center justify-between"><SectionTitle title="Трафик" subtitle="Freshness-aware"/><div className="flex gap-2"><Button variant={period==='24h'?'primary':'secondary'} onClick={()=>setPeriod('24h')}>24ч</Button><Button variant={period==='7d'?'primary':'secondary'} onClick={()=>setPeriod('7d')}>7д</Button></div></div>
                  <div className="h-64"><ResponsiveContainer width="100%" height="100%"><AreaChart data={chartData}><defs><linearGradient id="traffic" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#6366f1" stopOpacity={0.6}/><stop offset="95%" stopColor="#6366f1" stopOpacity={0.05}/></linearGradient></defs><CartesianGrid stroke="rgba(148,163,184,0.12)"/><XAxis dataKey="label" stroke="#94a3b8"/><YAxis stroke="#94a3b8"/><Tooltip/><Area type="monotone" dataKey="value" stroke="#818cf8" fill="url(#traffic)"/></AreaChart></ResponsiveContainer></div>
                </Card>
              </div>
            )}

            {tab === 'links' && <LinksView links={links} openActionCenter={openActionCenter} addSavedView={addSavedView} savedViews={savedViews} />}
            {tab === 'clients' && <ClientsView clients={clients} openActionCenter={openActionCenter} addSavedView={addSavedView} savedViews={savedViews} />}
            {tab === 'sessions' && <SessionsView sessions={sessions} onOpenSession={openSession} addSavedView={addSavedView} savedViews={savedViews} />}
            {tab === 'settings' && <SettingsView server={server} logs={logs} />}
          </>
        )}

        <CreateLinkModal open={openCreate} onOpenChange={setOpenCreate} onDone={load} />
        <NotificationCenter open={openNotifications} onOpenChange={setOpenNotifications} notifications={notifications} onRead={async (id)=>{await apiFetch(`/api/notifications/${id}/read`,{method:'POST'}); await load()}} onReadAll={async ()=>{await apiFetch('/api/notifications/read-all',{method:'POST'}); await load()}} />
        <ActionCenterModal open={openAction} onOpenChange={setOpenAction} payload={actionPayload} reason={actionReason} setReason={setActionReason} onConfirm={runAction} running={actionRunning} />
        <SessionDrilldownDrawer open={selectedSessionId !== null} onOpenChange={(v) => !v && setSelectedSessionId(null)} loading={sessionDrilldownLoading} data={sessionDrilldown} timeline={sessionTimeline} onGoLink={() => setTab('links')} onGoClient={() => setTab('clients')} />

        <div className="pointer-events-none fixed right-4 top-4 z-40 space-y-2">
          {pushNotices.map((n)=><div key={n.id} className={cn('pointer-events-auto w-80 rounded-xl border p-3 shadow-soft', n.tone==='warning' ? 'border-amber-400/40 bg-amber-500/10':'border-indigo-400/40 bg-indigo-500/10')}><p className="text-sm font-semibold">{n.title}</p><p className="text-xs text-muted">{n.message}</p></div>)}
        </div>
      </div>
    </div>
  )
}

function SavedViewsBar({ savedViews, onApply }: { savedViews: SavedView[]; onApply: (v: SavedView) => void }) {
  return <div className="mb-2 flex flex-wrap gap-2">{savedViews.length === 0 ? <span className="text-xs text-muted">Нет сохранённых представлений</span> : savedViews.map((v) => <Button key={v.name} variant="ghost" onClick={() => onApply(v)}>{v.name}</Button>)}</div>
}

function LinksView({ links, openActionCenter, addSavedView, savedViews }: { links: Link[]; openActionCenter: (a: ActionExecuteIn) => void; addSavedView: (v: SavedView) => void; savedViews: SavedView[] }) {
  const [q, setQ] = useState('')
  const [status, setStatus] = useState('all')
  const filtered = links.filter((l) => (status === 'all' || l.status === status) && (l.name.toLowerCase().includes(q.toLowerCase()) || l.tag.toLowerCase().includes(q.toLowerCase())))
  return (
    <Card>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2"><SectionTitle title="VLESS ссылки" subtitle="Центр действий + Saved Views"/><div className="flex gap-2"><Input value={q} onChange={(e)=>setQ(e.target.value)} placeholder="Поиск"/><Button onClick={() => addSavedView({ name: `Представление ${Date.now()}`, query: q, status })}>Сохранить view</Button></div></div>
      <SavedViewsBar savedViews={savedViews} onApply={(v) => { setQ(v.query); setStatus(v.status) }} />
      <div className="mb-2 flex gap-2"><Button variant={status==='all'?'primary':'secondary'} onClick={() => setStatus('all')}>Все</Button><Button variant={status==='active'?'primary':'secondary'} onClick={() => setStatus('active')}>Активные</Button><Button variant={status==='disabled'?'primary':'secondary'} onClick={() => setStatus('disabled')}>Отключённые</Button></div>
      {filtered.length===0?<EmptyState title="Нет ссылок" subtitle="Измените фильтры или создайте новую"/>:<div className="max-h-[62vh] overflow-auto"><table className="w-full min-w-[860px] text-sm"><thead className="sticky top-0 bg-panel"><tr className="text-left text-muted"><th>Имя</th><th>Статус</th><th>IP</th><th>Активность</th><th>Трафик</th><th>Лимит</th><th>Действия</th></tr></thead><tbody>{filtered.map((l)=><tr key={l.id} className="border-t border-border"><td>{l.name}</td><td><Badge tone={toneByStatus(l.status) as any}>{statusLabel[l.status] ?? l.status}</Badge></td><td className="font-['JetBrains_Mono'] text-xs">{l.last_ip ?? '—'}</td><td>{formatDate(l.last_activity_at)}</td><td>{formatTraffic(l.total_traffic_gb)}</td><td>{l.traffic_limit_gb ?? '—'}</td><td className="space-x-1"><Button variant="secondary" onClick={()=>navigator.clipboard.writeText(l.vless_url)}>Copy</Button><Button variant="secondary" onClick={()=>openActionCenter({ action: 'regenerate_uuid', target_type: 'link', target_id: l.id })}>UUID</Button><Button variant="secondary" onClick={()=>openActionCenter({ action: 'set_link_enabled', target_type: 'link', target_id: l.id, enabled: !l.enabled })}>{l.enabled?'Off':'On'}</Button></td></tr>)}</tbody></table></div>}
    </Card>
  )
}

function ClientsView({ clients, openActionCenter, addSavedView, savedViews }: { clients: Client[]; openActionCenter: (a: ActionExecuteIn) => void; addSavedView: (v: SavedView) => void; savedViews: SavedView[] }) {
  const [selectedId, setSelectedId] = useState<number | null>(clients[0]?.id ?? null)
  const [q, setQ] = useState('')
  const filtered = clients.filter((c) => c.client_name.toLowerCase().includes(q.toLowerCase()) || c.current_ip.includes(q))
  const selected = filtered.find((c) => c.id === selectedId) ?? null
  return <div className="grid gap-3 lg:grid-cols-3"><Card className="lg:col-span-1"><div className="mb-2 flex items-center justify-between"><SectionTitle title="Клиенты" subtitle="Список"/><Button variant="secondary" onClick={() => addSavedView({ name: `Представление ${Date.now()}`, query: q, status: 'all' })}>Сохранить view</Button></div><SavedViewsBar savedViews={savedViews} onApply={(v)=>setQ(v.query)} /><Input value={q} onChange={(e)=>setQ(e.target.value)} placeholder="Поиск"/>{filtered.map((c)=><button key={c.id} onClick={()=>setSelectedId(c.id)} className={cn('mt-2 w-full rounded-xl border p-3 text-left', selectedId===c.id?'border-indigo-400 bg-indigo-500/10':'border-border bg-bg')}><div className="flex justify-between"><span>{c.client_name}</span><Badge tone={c.status==='active'?'success':'default'}>{statusLabel[c.status] ?? c.status}</Badge></div></button>)}</Card><Card className="lg:col-span-2">{!selected?<LoadingState text="Выберите клиента"/>:<><SectionTitle title="Детали клиента" subtitle="Быстрые действия"/><p>{selected.client_name}</p><p className="font-['JetBrains_Mono'] text-sm">{selected.current_ip}</p><p className="text-sm">24ч: {formatTraffic(selected.traffic_24h_gb)} • 7д: {formatTraffic(selected.traffic_7d_gb)}</p><div className="mt-3"><Button variant="danger" onClick={() => openActionCenter({ action: 'mark_suspicious', target_type: 'client', target_id: selected.id })}>Пометить подозрительным</Button></div></>}</Card></div>
}

function SessionsView({ sessions, onOpenSession, addSavedView, savedViews }: { sessions: SessionItem[]; onOpenSession: (id: number) => void; addSavedView: (v: SavedView) => void; savedViews: SavedView[] }) {
  const [status, setStatus] = useState('all')
  const [q, setQ] = useState('')
  const filtered = sessions.filter((s) => (status === 'all' || s.status === status) && (s.client_name.toLowerCase().includes(q.toLowerCase()) || s.source_ip.includes(q)))
  return <Card><div className="mb-3 flex flex-wrap items-center justify-between gap-2"><SectionTitle title="Сессии" subtitle="Drilldown сессий + Timeline"/><div className="flex gap-2"><Input value={q} onChange={(e)=>setQ(e.target.value)} placeholder="Поиск"/><Button variant="secondary" onClick={() => addSavedView({ name: `Представление ${Date.now()}`, query: q, status })}>Сохранить view</Button></div></div><SavedViewsBar savedViews={savedViews} onApply={(v) => { setQ(v.query); setStatus(v.status) }} /><div className="mb-2 flex gap-2"><Button variant={status==='all'?'primary':'secondary'} onClick={() => setStatus('all')}>Все</Button><Button variant={status==='active'?'primary':'secondary'} onClick={() => setStatus('active')}>Активные</Button><Button variant={status==='closed'?'primary':'secondary'} onClick={() => setStatus('closed')}>Завершённые</Button></div>{filtered.length===0 ? <EmptyState title="Нет сессий" subtitle="Измените фильтр"/> : <div className="max-h-[60vh] overflow-auto"><table className="w-full min-w-[860px] text-sm"><thead className="sticky top-0 bg-panel"><tr className="text-left text-muted"><th>IP</th><th>Клиент</th><th>Ссылка</th><th>Статус</th><th>Старт</th><th>Длительность</th><th>IN/OUT</th></tr></thead><tbody>{filtered.map((s)=><tr key={s.id} onClick={() => onOpenSession(s.id)} className="cursor-pointer border-t border-border hover:bg-indigo-500/10"><td className="font-['JetBrains_Mono'] text-xs">{s.source_ip}</td><td>{s.client_name}</td><td>{s.link_name}</td><td><Badge tone={toneByStatus(s.status) as any}>{statusLabel[s.status] ?? s.status}</Badge></td><td>{formatDate(s.started_at)}</td><td>{Math.floor(s.duration_sec/60)} мин</td><td>{s.inbound_gb.toFixed(2)} / {s.outbound_gb.toFixed(2)} GB</td></tr>)}</tbody></table></div>}</Card>
}

function SettingsView({ server, logs }: { server: ServerStatus | null; logs: LogItem[] }) {
  const [serverLogs, setServerLogs] = useState<string[]>([])
  useEffect(() => { apiFetch<{ lines: string[] }>('/api/server/logs').then((x) => setServerLogs(x.lines)).catch(() => setServerLogs([])) }, [])
  return <div className="grid gap-3 lg:grid-cols-2"><Card><SectionTitle title="Состояние сервера" subtitle="Основные параметры"/><p>Статус: <Badge tone={toneByStatus(server?.service_status) as any}>{statusLabel[server?.service_status ?? ''] ?? server?.service_status ?? 'unknown'}</Badge></p><p>Версия: {server?.xray_version ?? '—'}</p><p>Uptime: {server?.uptime_hours ?? 0} часов</p><p>Адрес: {server?.domain ?? '—'}:{server?.port ?? '—'}</p></Card><Card><SectionTitle title="Логи и активность"/><div className="rounded-xl border border-border bg-bg p-3 font-['JetBrains_Mono'] text-xs">{serverLogs.length===0 ? 'Логи недоступны' : serverLogs.map((l,i)=><p key={i}>{l}</p>)}</div><div className="mt-3 max-h-44 overflow-auto rounded-xl border border-border bg-bg p-3 text-sm">{logs.map((l)=><p key={l.id}><span className="text-muted">{formatDate(l.created_at)}</span> — {l.action}</p>)}</div></Card></div>
}

function NotificationCenter({ open, onOpenChange, notifications, onRead, onReadAll }: { open: boolean; onOpenChange: (v: boolean) => void; notifications: NotificationItem[]; onRead: (id:number)=>Promise<void>; onReadAll: ()=>Promise<void> }) {
  return <Modal open={open} onOpenChange={onOpenChange} title="Notification Center"><div className="mb-2 flex justify-end"><Button variant="secondary" onClick={() => onReadAll()}>Прочитать все</Button></div>{notifications.length===0 ? <EmptyState title="Уведомлений нет" subtitle="События появятся здесь."/> : <div className="max-h-[60vh] space-y-2 overflow-auto">{notifications.map((n)=><div key={n.id} className={cn('rounded-xl border p-3', n.is_read ? 'border-border bg-bg':'border-indigo-400/40 bg-indigo-500/10')}><div className="flex items-center justify-between"><Badge tone={n.severity==='warning'?'warn':'info'}>{n.severity}</Badge><span className="text-xs text-muted">{formatDate(n.created_at)}</span></div><p className="mt-1 text-sm font-medium">{n.title}</p><p className="text-xs text-muted">{n.message}</p>{!n.is_read && <Button variant="ghost" className="mt-1" onClick={() => onRead(n.id)}>Отметить прочитанным</Button>}</div>)}</div>}</Modal>
}

function ActionCenterModal({ open, onOpenChange, payload, reason, setReason, onConfirm, running }: { open: boolean; onOpenChange: (v: boolean) => void; payload: ActionExecuteIn | null; reason: string; setReason: (v: string) => void; onConfirm: () => Promise<void>; running: boolean }) {
  const consequences: Record<string, string> = {
    restart: 'Перезапуск кратковременно прервёт активные подключения.',
    reload: 'Перезагрузка конфигурации применит изменения без полного рестарта.',
    regenerate_uuid: 'Старый UUID ссылки перестанет работать.',
    set_link_enabled: 'Смена статуса ссылки влияет на доступ клиента.',
    mark_suspicious: 'Клиент будет отмечен для диагностики и аудита.'
  }
  return <Modal open={open} onOpenChange={onOpenChange} title="Центр действий"><div className="space-y-3">{!payload ? <LoadingState text="Нет действия"/> : <><p className="text-sm">Действие: <b>{payload.action}</b></p><p className="text-sm text-muted">{consequences[payload.action]}</p><Input value={reason} onChange={(e)=>setReason(e.target.value)} placeholder="Причина / комментарий (опционально)"/><div className="flex justify-end gap-2"><Button variant="secondary" onClick={() => onOpenChange(false)}>Отмена</Button><Button onClick={() => { void onConfirm() }} disabled={running}>{running ? 'Выполняется...' : 'Подтвердить'}</Button></div></>}</div></Modal>
}

function SessionDrilldownDrawer({ open, onOpenChange, loading, data, timeline, onGoClient, onGoLink }: { open: boolean; onOpenChange: (v: boolean) => void; loading: boolean; data: SessionDrilldown | null; timeline: TimelineEvent[]; onGoClient: () => void; onGoLink: () => void }) {
  return <Modal open={open} onOpenChange={onOpenChange} title="Drilldown сессии">{loading ? <LoadingState text="Загрузка деталей сессии..."/> : !data ? <ErrorState message="Не удалось загрузить детали"/> : <div className="space-y-3"><div className="grid gap-2 md:grid-cols-2"><Card><p className="text-xs text-muted">IP источника</p><p className="font-['JetBrains_Mono'] text-sm">{data.source_ip}</p></Card><Card><p className="text-xs text-muted">Статус</p><Badge tone={toneByStatus(data.status) as any}>{statusLabel[data.status] ?? data.status}</Badge></Card><Card><p className="text-xs text-muted">Время старта</p><p>{formatDate(data.started_at)}</p></Card><Card><p className="text-xs text-muted">Длительность</p><p>{Math.floor(data.duration_sec / 60)} мин</p></Card><Card><p className="text-xs text-muted">Трафик</p><p>IN {data.inbound_gb.toFixed(2)} / OUT {data.outbound_gb.toFixed(2)} GB</p></Card><Card><p className="text-xs text-muted">Reconnect/история</p><p>{data.reconnect_summary}</p></Card></div><div className="flex gap-2"><Button variant="secondary" onClick={onGoClient}>К клиенту</Button><Button variant="secondary" onClick={onGoLink}>К ссылке</Button></div><Card><SectionTitle title="Timeline / Корреляция" subtitle="События по сессии"/>{timeline.length === 0 ? <EmptyState title="Событий пока нет" subtitle="Появятся после активности"/> : <div className="space-y-2">{timeline.map((t, idx) => <div key={`${t.at}-${idx}`} className="rounded-xl border border-border bg-bg p-3"><div className="flex justify-between"><Badge tone={t.kind === 'system' ? 'warn' : 'info'}>{t.kind}</Badge><span className="text-xs text-muted">{formatDate(t.at)}</span></div><p className="mt-1 text-sm font-medium">{t.title}</p><p className="text-xs text-muted">{t.message}</p></div>)}</div>}</Card><Card><SectionTitle title="Связанные события"/>{data.related_events.length === 0 ? <EmptyState title="Нет связанных событий" subtitle="События появятся позже"/> : data.related_events.map((e, idx) => <p key={idx} className="text-sm"><span className="text-muted">{formatDate(e.created_at)}</span> — {e.title}: {e.message}</p>)}</Card></div>}</Modal>
}

function CreateLinkModal({ open, onOpenChange, onDone }: { open: boolean; onOpenChange: (v: boolean) => void; onDone: () => void }) {
  const [name, setName] = useState('')
  const [tag, setTag] = useState('Test device')
  const [note, setNote] = useState('')
  const [limit, setLimit] = useState('40')
  return <Modal open={open} onOpenChange={onOpenChange} title="Создать VLESS ссылку"><div className="grid gap-2"><Input placeholder="Имя" value={name} onChange={(e)=>setName(e.target.value)} /><Input placeholder="Тег" value={tag} onChange={(e)=>setTag(e.target.value)} /><Input placeholder="Заметка" value={note} onChange={(e)=>setNote(e.target.value)} /><Input placeholder="Лимит GB" value={limit} onChange={(e)=>setLimit(e.target.value)} /><div className="flex justify-end gap-2"><Button variant="secondary" onClick={()=>onOpenChange(false)}>Отмена</Button><Button onClick={async()=>{await apiFetch('/api/links',{method:'POST',body:JSON.stringify({name,tag,note:note||'Создано из UI',traffic_limit_gb:Number(limit),enabled:true})}); setName(''); setTag('Test device'); setNote(''); setLimit('40'); onOpenChange(false); onDone()}}>Создать</Button></div></div></Modal>
}
