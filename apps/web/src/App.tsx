import { useEffect, useMemo, useState } from 'react'
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Badge, Button, Card, EmptyState, ErrorState, InlineNotice, Input, LoadingState, Modal, SectionTitle, SkeletonBlock } from './components/ui'
import { apiFetch, apiToken, cn } from './lib/utils'
import type { Client, Link, NotificationItem, Overview, ServerStatus, SessionItem } from './types/api'

type TabKey = 'dashboard' | 'links' | 'clients' | 'sessions' | 'settings'
type EventItem = { id: number; title: string; message: string; level: string; created_at: string }
type LogItem = { id: number; action: string; status: string; created_at: string }
type PushNotice = { id: number; title: string; message: string; tone: 'info' | 'warning' }

const statusLabel: Record<string, string> = { active: 'Активен', idle: 'Неактивен', disabled: 'Отключен', running: 'Работает', closed: 'Завершена' }
const dateTime = new Intl.DateTimeFormat('ru-RU', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })

function formatTraffic(value: number) { return `${value.toFixed(1)} GB` }
function formatDate(value?: string | null) { if (!value) return '—'; return dateTime.format(new Date(value)) }
function toneByStatus(status?: string) { if (status === 'active' || status === 'running') return 'success'; if (status === 'disabled') return 'danger'; if (status === 'idle' || status === 'closed') return 'default'; return 'info' }

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
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [pushEnabled, setPushEnabled] = useState(true)
  const [pushNotices, setPushNotices] = useState<PushNotice[]>([])
  const [period, setPeriod] = useState<'24h' | '7d'>('24h')
  const [openCreate, setOpenCreate] = useState(false)
  const [openNotifications, setOpenNotifications] = useState(false)

  async function load() {
    setLoading(true)
    setError(null)
    try {
      const [ov, ls, cs, ss, sv, ev, lg, nt] = await Promise.all([
        apiFetch<Overview>('/api/dashboard/overview'),
        apiFetch<Link[]>('/api/links'),
        apiFetch<Client[]>('/api/clients'),
        apiFetch<SessionItem[]>('/api/sessions/active'),
        apiFetch<ServerStatus>('/api/server/status'),
        apiFetch<EventItem[]>('/api/events'),
        apiFetch<LogItem[]>('/api/activity-log'),
        apiFetch<NotificationItem[]>('/api/notifications')
      ])
      setOverview(ov); setLinks(ls); setClients(cs); setSessions(ss); setServer(sv); setEvents(ev); setLogs(lg); setNotifications(nt)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    const base = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
    const src = new EventSource(`${base}/api/events/stream?token=${apiToken}`)
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
        }
      } catch {}
      void load()
    }
    src.onerror = () => src.close()
    return () => src.close()
  }, [pushEnabled])

  useEffect(() => { if (!notice) return; const t = setTimeout(() => setNotice(null), 2200); return () => clearTimeout(t) }, [notice])
  useEffect(() => { if (!pushNotices.length) return; const t = setTimeout(() => setPushNotices((prev) => prev.slice(0, -1)), 6000); return () => clearTimeout(t) }, [pushNotices])

  const chartData = useMemo(() => (period === '24h' ? overview?.chart_24h ?? [] : overview?.chart_7d ?? []), [period, overview])

  return (
    <div className="min-h-screen bg-bg p-4 font-['Inter'] text-slate-100 md:p-6">
      <div className="mx-auto max-w-7xl space-y-5">
        <header className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-border bg-panel p-4 shadow-soft">
          <div><h1 className="text-xl font-semibold md:text-2xl">Панель управления Xray / VLESS</h1><p className="text-sm text-muted">Foundation Sprint baseline</p></div>
          <nav className="flex flex-wrap gap-2">
            {([['dashboard','Дашборд'],['links','VLESS ссылки'],['clients','Клиенты'],['sessions','Сессии'],['settings','Настройки']] as const).map(([k,l]) => (
              <button key={k} onClick={() => setTab(k)} className={cn('rounded-xl px-3 py-2 text-sm transition', tab===k ? 'bg-indigo-500 text-white':'bg-slate-700/40 text-slate-200 hover:bg-slate-700/70')}>{l}</button>
            ))}
          </nav>
          <div className="flex gap-2"><Button variant="ghost" onClick={() => setPushEnabled((v)=>!v)}>{pushEnabled ? 'Push: Вкл':'Push: Выкл'}</Button><Button variant="secondary" onClick={() => setOpenNotifications(true)}>Уведомления ({notifications.filter(n=>!n.is_read).length})</Button></div>
        </header>

        {notice && <InlineNotice text={notice} tone="info" />}
        {error && <ErrorState message={`Ошибка загрузки: ${error}`} onRetry={load} />}
        {loading && <SkeletonBlock rows={6} />}

        {!loading && tab === 'dashboard' && (
          <div className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <KpiCard title="Всего ссылок" value={String(overview?.total_links ?? 0)} subtitle="Активных и резервных" />
              <KpiCard title="Активные подключения" value={String(overview?.active_connections ?? 0)} subtitle="Онлайн сейчас" />
              <KpiCard title="Трафик за 24ч" value={formatTraffic(overview?.traffic_24h_gb ?? 0)} subtitle="Суммарно" />
              <Card><SectionTitle title="Статус Xray" subtitle="Текущее состояние" /><Badge tone={toneByStatus(overview?.server_status) as any}>{statusLabel[overview?.server_status ?? ''] ?? overview?.server_status ?? 'unknown'}</Badge></Card>
            </div>
            <Card><div className="mb-3 flex items-center justify-between"><SectionTitle title="График трафика" subtitle="24ч/7д" /><div className="flex gap-2"><Button variant={period==='24h'?'primary':'secondary'} onClick={()=>setPeriod('24h')}>24 часа</Button><Button variant={period==='7d'?'primary':'secondary'} onClick={()=>setPeriod('7d')}>7 дней</Button></div></div><div className="h-64">{chartData.length===0 ? <EmptyState title="Нет данных" subtitle="Ожидаем трафик" /> : <ResponsiveContainer width="100%" height="100%"><AreaChart data={chartData}><CartesianGrid stroke="#24324f" strokeDasharray="3 3" /><XAxis dataKey="label" stroke="#8ea0c8" /><YAxis stroke="#8ea0c8" /><Tooltip /><Area type="monotone" dataKey="value" stroke="#818cf8" fill="#6366f133" /></AreaChart></ResponsiveContainer>}</div></Card>
          </div>
        )}

        {!loading && tab === 'links' && <LinksView links={links} reload={load} onCreate={() => setOpenCreate(true)} setNotice={setNotice} />}
        {!loading && tab === 'clients' && <ClientsView clients={clients} />}
        {!loading && tab === 'sessions' && <SessionsView sessions={sessions} onReload={load} />}
        {!loading && tab === 'settings' && <SettingsView server={server} logs={logs} />}
      </div>

      <CreateLinkModal open={openCreate} onOpenChange={setOpenCreate} onDone={() => { setNotice('Ссылка создана'); return load() }} />
      <NotificationCenter open={openNotifications} onOpenChange={setOpenNotifications} notifications={notifications} onRead={async (id)=>{await apiFetch(`/api/notifications/${id}/read`,{method:'POST'}); await load()}} onReadAll={async ()=>{await apiFetch('/api/notifications/read-all',{method:'POST'}); await load()}} />

      {pushNotices.length > 0 && <div className="fixed right-4 top-4 z-30 w-[min(92vw,360px)] space-y-2">{pushNotices.map((n)=><div key={n.id} className="rounded-xl border border-border bg-panel p-3 shadow-soft"><Badge tone={n.tone==='warning'?'warn':'info'}>{n.tone==='warning'?'Внимание':'Уведомление'}</Badge><p className="mt-1 text-sm font-medium">{n.title}</p><p className="text-xs text-muted">{n.message}</p></div>)}</div>}
    </div>
  )
}

function KpiCard({ title, value, subtitle }: { title: string; value: string; subtitle: string }) { return <Card><p className="text-sm text-muted">{title}</p><p className="mt-1 text-2xl font-semibold">{value}</p><p className="text-xs text-muted">{subtitle}</p></Card> }

function NotificationCenter({ open, onOpenChange, notifications, onRead, onReadAll }: { open: boolean; onOpenChange: (v: boolean) => void; notifications: NotificationItem[]; onRead: (id:number)=>Promise<void>; onReadAll: ()=>Promise<void> }) {
  return <Modal open={open} onOpenChange={onOpenChange} title="Notification Center"><div className="mb-2 flex justify-end"><Button variant="secondary" onClick={() => onReadAll()}>Прочитать все</Button></div>{notifications.length===0 ? <EmptyState title="Уведомлений нет" subtitle="События появятся здесь."/> : <div className="max-h-[60vh] space-y-2 overflow-auto">{notifications.map((n)=><div key={n.id} className={cn('rounded-xl border p-3', n.is_read ? 'border-border bg-bg':'border-indigo-400/40 bg-indigo-500/10')}><div className="flex items-center justify-between"><Badge tone={n.severity==='warning'?'warn':'info'}>{n.severity}</Badge><span className="text-xs text-muted">{formatDate(n.created_at)}</span></div><p className="mt-1 text-sm font-medium">{n.title}</p><p className="text-xs text-muted">{n.message}</p>{!n.is_read && <Button variant="ghost" className="mt-1" onClick={() => onRead(n.id)}>Отметить прочитанным</Button>}</div>)}</div>}</Modal>
}

function SessionsView({ sessions, onReload }: { sessions: SessionItem[]; onReload: () => void }) {
  const [status, setStatus] = useState<'all'|'active'|'closed'>('all')
  const data = sessions.filter(s => status==='all' ? true : s.status===status)
  return <Card><div className="mb-3 flex items-center justify-between"><SectionTitle title="Active Sessions" subtitle="Отдельный модуль сессий" /><div className="flex gap-2"><Button variant={status==='all'?'primary':'secondary'} onClick={()=>setStatus('all')}>Все</Button><Button variant={status==='active'?'primary':'secondary'} onClick={()=>setStatus('active')}>Активные</Button><Button variant={status==='closed'?'primary':'secondary'} onClick={()=>setStatus('closed')}>Завершённые</Button><Button variant="secondary" onClick={onReload}>Обновить</Button></div></div>{data.length===0 ? <EmptyState title="Сессий нет" subtitle="Проверьте фильтры"/> : <div className="max-h-[62vh] overflow-auto"><table className="w-full min-w-[760px] text-sm"><thead className="sticky top-0 bg-panel"><tr className="text-left text-muted"><th>Client</th><th>Link</th><th>Source IP</th><th>Started</th><th>Duration</th><th>In/Out</th><th>Status</th></tr></thead><tbody>{data.map((s)=><tr key={s.id} className="border-t border-border"><td>{s.client_name}</td><td>{s.link_name}</td><td className="font-['JetBrains_Mono'] text-xs">{s.source_ip}</td><td>{formatDate(s.started_at)}</td><td>{Math.floor(s.duration_sec/60)} мин</td><td>{s.inbound_gb.toFixed(2)} / {s.outbound_gb.toFixed(2)} GB</td><td><Badge tone={toneByStatus(s.status) as any}>{statusLabel[s.status] ?? s.status}</Badge></td></tr>)}</tbody></table></div>}</Card>
}

function LinksView({ links, reload, onCreate, setNotice }: { links: Link[]; reload: () => void; onCreate: () => void; setNotice: (v: string | null) => void }) {
  const [q, setQ] = useState('')
  const filtered = links.filter((l) => l.name.toLowerCase().includes(q.toLowerCase()) || l.tag.toLowerCase().includes(q.toLowerCase()))
  async function action(id: number, type: 'delete' | 'regenerate' | 'toggle') {
    if (type === 'delete') { if (!confirm('Удалить ссылку?')) return; await apiFetch(`/api/links/${id}`, { method: 'DELETE' }); setNotice('Ссылка удалена') }
    if (type === 'regenerate') { await apiFetch(`/api/links/${id}/regenerate`, { method: 'POST' }); setNotice('UUID обновлён') }
    if (type === 'toggle') { const link = links.find((i) => i.id === id); if (!link) return; await apiFetch(`/api/links/${id}`, { method: 'PATCH', body: JSON.stringify({ enabled: !link.enabled }) }); setNotice(link.enabled ? 'Ссылка отключена' : 'Ссылка включена') }
    await reload()
  }
  return <Card><div className="mb-3 flex flex-wrap items-center justify-between gap-2"><SectionTitle title="VLESS ссылки" subtitle="Search + CRUD + actions"/><div className="flex gap-2"><Input value={q} onChange={(e)=>setQ(e.target.value)} placeholder="Поиск"/><Button onClick={onCreate}>Создать</Button></div></div>{filtered.length===0?<EmptyState title="Нет ссылок" subtitle="Создайте новую"/>:<div className="max-h-[62vh] overflow-auto"><table className="w-full min-w-[860px] text-sm"><thead className="sticky top-0 bg-panel"><tr className="text-left text-muted"><th>Имя</th><th>Статус</th><th>IP</th><th>Активность</th><th>Трафик</th><th>Лимит</th><th>Действия</th></tr></thead><tbody>{filtered.map((l)=><tr key={l.id} className="border-t border-border"><td>{l.name}</td><td><Badge tone={toneByStatus(l.status) as any}>{statusLabel[l.status] ?? l.status}</Badge></td><td className="font-['JetBrains_Mono'] text-xs">{l.last_ip ?? '—'}</td><td>{formatDate(l.last_activity_at)}</td><td>{formatTraffic(l.total_traffic_gb)}</td><td>{l.traffic_limit_gb ?? '—'}</td><td className="space-x-1"><Button variant="secondary" onClick={()=>navigator.clipboard.writeText(l.vless_url)}>Copy</Button><Button variant="secondary" onClick={()=>action(l.id,'regenerate')}>UUID</Button><Button variant="secondary" onClick={()=>action(l.id,'toggle')}>{l.enabled?'Off':'On'}</Button><Button variant="danger" onClick={()=>action(l.id,'delete')}>Del</Button></td></tr>)}</tbody></table></div>}</Card>
}

function ClientsView({ clients }: { clients: Client[] }) {
  const [selectedId, setSelectedId] = useState<number | null>(clients[0]?.id ?? null)
  const selected = clients.find((c) => c.id === selectedId) ?? null
  return <div className="grid gap-3 lg:grid-cols-3"><Card className="lg:col-span-1"><SectionTitle title="Clients" subtitle="Список"/>{clients.map((c)=><button key={c.id} onClick={()=>setSelectedId(c.id)} className={cn('mb-2 w-full rounded-xl border p-3 text-left', selectedId===c.id?'border-indigo-400 bg-indigo-500/10':'border-border bg-bg')}><div className="flex justify-between"><span>{c.client_name}</span><Badge tone={c.status==='active'?'success':'default'}>{statusLabel[c.status] ?? c.status}</Badge></div></button>)}</Card><Card className="lg:col-span-2">{!selected?<LoadingState text="Выберите клиента"/>:<><SectionTitle title="Детали клиента"/><p>{selected.client_name}</p><p className="font-['JetBrains_Mono'] text-sm">{selected.current_ip}</p><p className="text-sm">24ч: {formatTraffic(selected.traffic_24h_gb)} • 7д: {formatTraffic(selected.traffic_7d_gb)}</p></>}</Card></div>
}

function SettingsView({ server, logs }: { server: ServerStatus | null; logs: LogItem[] }) {
  const [serverLogs, setServerLogs] = useState<string[]>([])
  useEffect(() => { apiFetch<{ lines: string[] }>('/api/server/logs').then((x) => setServerLogs(x.lines)).catch(() => setServerLogs([])) }, [])
  return <div className="grid gap-3 lg:grid-cols-2"><Card><SectionTitle title="Состояние сервера" subtitle="Основные параметры"/><p>Статус: <Badge tone={toneByStatus(server?.service_status) as any}>{statusLabel[server?.service_status ?? ''] ?? server?.service_status ?? 'unknown'}</Badge></p><p>Версия: {server?.xray_version ?? '—'}</p><p>Uptime: {server?.uptime_hours ?? 0} часов</p><p>Адрес: {server?.domain ?? '—'}:{server?.port ?? '—'}</p></Card><Card><SectionTitle title="Логи и активность"/><div className="rounded-xl border border-border bg-bg p-3 font-['JetBrains_Mono'] text-xs">{serverLogs.length===0 ? 'Логи недоступны' : serverLogs.map((l,i)=><p key={i}>{l}</p>)}</div><div className="mt-3 max-h-44 overflow-auto rounded-xl border border-border bg-bg p-3 text-sm">{logs.map((l)=><p key={l.id}><span className="text-muted">{formatDate(l.created_at)}</span> — {l.action}</p>)}</div></Card></div>
}

function CreateLinkModal({ open, onOpenChange, onDone }: { open: boolean; onOpenChange: (v: boolean) => void; onDone: () => void }) {
  const [name, setName] = useState('')
  const [tag, setTag] = useState('Test device')
  const [note, setNote] = useState('')
  const [limit, setLimit] = useState('40')
  return <Modal open={open} onOpenChange={onOpenChange} title="Создать VLESS ссылку"><div className="grid gap-2"><Input placeholder="Имя" value={name} onChange={(e)=>setName(e.target.value)} /><Input placeholder="Тег" value={tag} onChange={(e)=>setTag(e.target.value)} /><Input placeholder="Заметка" value={note} onChange={(e)=>setNote(e.target.value)} /><Input placeholder="Лимит GB" value={limit} onChange={(e)=>setLimit(e.target.value)} /><div className="flex justify-end gap-2"><Button variant="secondary" onClick={()=>onOpenChange(false)}>Отмена</Button><Button onClick={async()=>{await apiFetch('/api/links',{method:'POST',body:JSON.stringify({name,tag,note:note||'Создано из UI',traffic_limit_gb:Number(limit),enabled:true})}); setName(''); setTag('Test device'); setNote(''); setLimit('40'); onOpenChange(false); onDone()}}>Создать</Button></div></div></Modal>
}
