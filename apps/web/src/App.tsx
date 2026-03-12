import { useEffect, useMemo, useState } from 'react'
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Badge, Button, Card, EmptyState, Input, Modal, SectionTitle } from './components/ui'
import { apiFetch, apiToken, cn } from './lib/utils'
import type { Client, Link, Overview, ServerStatus } from './types/api'

type TabKey = 'dashboard' | 'links' | 'clients' | 'settings'
type EventItem = { id: number; title: string; message: string; level: string; created_at: string }
type LogItem = { id: number; action: string; status: string; created_at: string }
type PushNotice = { id: number; title: string; message: string; tone: 'info' | 'warning' }

const statusLabel: Record<string, string> = { active: 'Активен', idle: 'Неактивен', disabled: 'Отключен', running: 'Работает' }

const dateTime = new Intl.DateTimeFormat('ru-RU', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })

function formatTraffic(value: number) {
  return `${value.toFixed(1)} GB`
}

function formatDate(value?: string | null) {
  if (!value) return '—'
  return dateTime.format(new Date(value))
}

function toneByStatus(status?: string) {
  if (status === 'active' || status === 'running') return 'success'
  if (status === 'disabled') return 'danger'
  if (status === 'idle') return 'default'
  return 'info'
}

export function App() {
  const [tab, setTab] = useState<TabKey>('dashboard')
  const [overview, setOverview] = useState<Overview | null>(null)
  const [links, setLinks] = useState<Link[]>([])
  const [clients, setClients] = useState<Client[]>([])
  const [server, setServer] = useState<ServerStatus | null>(null)
  const [events, setEvents] = useState<EventItem[]>([])
  const [logs, setLogs] = useState<LogItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [pushEnabled, setPushEnabled] = useState(true)
  const [pushNotices, setPushNotices] = useState<PushNotice[]>([])
  const [period, setPeriod] = useState<'24h' | '7d'>('24h')
  const [openCreate, setOpenCreate] = useState(false)

  async function load() {
    setLoading(true)
    setError(null)
    try {
      const [ov, ls, cs, sv, ev, lg] = await Promise.all([
        apiFetch<Overview>('/api/dashboard/overview'),
        apiFetch<Link[]>('/api/links'),
        apiFetch<Client[]>('/api/clients'),
        apiFetch<ServerStatus>('/api/server/status'),
        apiFetch<EventItem[]>('/api/events'),
        apiFetch<LogItem[]>('/api/activity-log')
      ])
      setOverview(ov)
      setLinks(ls)
      setClients(cs)
      setServer(sv)
      setEvents(ev)
      setLogs(lg)
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
        const payload = JSON.parse(event.data) as { kind?: string; title?: string; message?: string; type?: string }
        if (payload.kind === 'notification' && payload.title && payload.message) {
          const tone: PushNotice['tone'] = payload.type === 'warning' ? 'warning' : 'info'
          const incoming: PushNotice = { id: Date.now(), title: payload.title, message: payload.message, tone }
          setPushNotices((prev) => [incoming, ...prev].slice(0, 4))
        }
      } catch {
        // ignore malformed events
      }
      void load()
    }
    src.onerror = () => src.close()
    return () => src.close()
  }, [pushEnabled])

  useEffect(() => {
    if (!notice) return
    const timeout = setTimeout(() => setNotice(null), 2400)
    return () => clearTimeout(timeout)
  }, [notice])

  useEffect(() => {
    if (!pushNotices.length) return
    const timeout = setTimeout(() => {
      setPushNotices((prev) => prev.slice(0, -1))
    }, 6000)
    return () => clearTimeout(timeout)
  }, [pushNotices])

  const chartData = useMemo(() => (period === '24h' ? overview?.chart_24h ?? [] : overview?.chart_7d ?? []), [period, overview])
  const activeClients = clients.filter((c) => c.status === 'active')

  return (
    <div className="min-h-screen bg-bg p-4 font-['Inter'] text-slate-100 md:p-6">
      <div className="mx-auto max-w-7xl space-y-5">
        <header className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-border bg-panel p-4 shadow-soft">
          <div>
            <h1 className="text-xl font-semibold md:text-2xl">Панель управления Xray / VLESS</h1>
            <p className="text-sm text-muted">Один сервер • единый контроль доступа и активности</p>
          </div>
          <nav className="flex flex-wrap gap-2">
            {([
              ['dashboard', 'Дашборд'],
              ['links', 'VLESS ссылки'],
              ['clients', 'Клиенты'],
              ['settings', 'Настройки сервера']
            ] as const).map(([k, l]) => (
              <button key={k} onClick={() => setTab(k)} className={cn('rounded-xl px-3 py-2 text-sm transition', tab === k ? 'bg-indigo-500 text-white' : 'bg-slate-700/40 text-slate-200 hover:bg-slate-700/70')}>
                {l}
              </button>
            ))}
          </nav>
          <Button variant="ghost" onClick={() => setPushEnabled((v) => !v)}>{pushEnabled ? 'Push: Вкл' : 'Push: Выкл'}</Button>
        </header>

        {notice && <Card className="border-indigo-400/40 text-indigo-200">{notice}</Card>}
        {pushNotices.length > 0 && (
          <div className="fixed right-4 top-4 z-30 w-[min(92vw,360px)] space-y-2">{pushNotices.map((n) => <div key={n.id} className="rounded-xl border border-border bg-panel p-3 shadow-soft"><div className="flex items-center justify-between"><Badge tone={n.tone === 'warning' ? 'warn' : 'info'}>{n.tone === 'warning' ? 'Внимание' : 'Уведомление'}</Badge><button className="text-xs text-muted hover:text-slate-100" onClick={() => setPushNotices((prev) => prev.filter((x) => x.id !== n.id))}>Закрыть</button></div><p className="mt-1 text-sm font-medium">{n.title}</p><p className="text-xs text-muted">{n.message}</p></div>)}</div>
        )}
        {error && <Card className="border-rose-500/40 text-rose-200">Ошибка загрузки: {error}</Card>}
        {loading && <Card className="text-muted">Загрузка данных панели…</Card>}

        {!loading && tab === 'dashboard' && (
          <div className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <KpiCard title="Всего ссылок" value={String(overview?.total_links ?? 0)} subtitle="Активных и резервных" />
              <KpiCard title="Активные подключения" value={String(overview?.active_connections ?? 0)} subtitle="Онлайн сейчас" />
              <KpiCard title="Трафик за 24ч" value={formatTraffic(overview?.traffic_24h_gb ?? 0)} subtitle="Суммарно по серверу" />
              <Card><SectionTitle title="Статус Xray" subtitle="Текущее состояние сервиса" /><Badge tone={toneByStatus(overview?.server_status) as any}>{statusLabel[overview?.server_status ?? ''] ?? overview?.server_status ?? 'unknown'}</Badge></Card>
            </div>

            <Card>
              <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                <SectionTitle title="График трафика" subtitle="Нагрузка по выбранному периоду" />
                <div className="flex gap-2">
                  <Button variant={period === '24h' ? 'primary' : 'secondary'} onClick={() => setPeriod('24h')}>24 часа</Button>
                  <Button variant={period === '7d' ? 'primary' : 'secondary'} onClick={() => setPeriod('7d')}>7 дней</Button>
                </div>
              </div>
              <div className="h-64">{chartData.length === 0 ? <EmptyState title="Нет данных по трафику" subtitle="Данные появятся после первой активности." /> : <ResponsiveContainer width="100%" height="100%"><AreaChart data={chartData}><CartesianGrid stroke="#24324f" strokeDasharray="3 3" /><XAxis dataKey="label" stroke="#8ea0c8" /><YAxis stroke="#8ea0c8" /><Tooltip /><Area type="monotone" dataKey="value" stroke="#818cf8" fill="#6366f133" /></AreaChart></ResponsiveContainer>}</div>
            </Card>

            <div className="grid gap-3 lg:grid-cols-3">
              <Card>
                <SectionTitle title="Активные сессии" subtitle="Клиенты в онлайне" />
                {activeClients.length === 0 ? <EmptyState title="Нет активных сессий" subtitle="Проверьте статус соединений позже." /> : activeClients.map((c) => <div key={c.id} className="mb-2 rounded-xl border border-border bg-bg p-3 text-sm"><div className="flex items-center justify-between"><p>{c.client_name}</p><Badge tone="success">Онлайн</Badge></div><p className="font-['JetBrains_Mono'] text-xs text-muted">{c.current_ip}</p></div>)}
              </Card>
              <Card>
                <SectionTitle title="Последние события" subtitle="Переподключения и уведомления" />
                {events.slice(0, 4).map((e) => <div key={e.id} className="mb-2 rounded-xl border border-border bg-bg p-3 text-sm"><div className="flex items-center justify-between"><Badge tone={e.level === 'warning' ? 'warn' : 'info'}>{e.title}</Badge><span className="text-xs text-muted">{formatDate(e.created_at)}</span></div><p className="mt-1 text-muted">{e.message}</p></div>)}
                {events.length === 0 && <EmptyState title="Событий пока нет" subtitle="Система работает стабильно." />}
              </Card>
              <Card>
                <SectionTitle title="Быстрые действия" subtitle="Частые операции администратора" />
                <div className="grid gap-2"><Button onClick={() => setOpenCreate(true)}>Создать ссылку</Button><Button variant="secondary" onClick={() => apiFetch('/api/server/restart', { method: 'POST' }).then(() => { setNotice('Команда перезапуска отправлена'); return load() })}>Перезапустить Xray</Button><Button variant="secondary" onClick={() => apiFetch('/api/server/reload', { method: 'POST' }).then(() => { setNotice('Команда перезагрузки отправлена'); return load() })}>Перезагрузить конфиг</Button></div>
              </Card>
            </div>
          </div>
        )}

        {!loading && tab === 'links' && <LinksView links={links} reload={load} onCreate={() => setOpenCreate(true)} setNotice={setNotice} />}
        {!loading && tab === 'clients' && <ClientsView clients={clients} />}
        {!loading && tab === 'settings' && <SettingsView server={server} logs={logs} />}
      </div>

      <CreateLinkModal open={openCreate} onOpenChange={setOpenCreate} onDone={() => { setNotice('Ссылка успешно создана'); return load() }} />
    </div>
  )
}

function KpiCard({ title, value, subtitle }: { title: string; value: string; subtitle: string }) {
  return <Card><p className="text-sm text-muted">{title}</p><p className="mt-1 text-2xl font-semibold tracking-tight">{value}</p><p className="mt-1 text-xs text-muted">{subtitle}</p></Card>
}

function LinksView({ links, reload, onCreate, setNotice }: { links: Link[]; reload: () => void; onCreate: () => void; setNotice: (v: string | null) => void }) {
  const [q, setQ] = useState('')
  const [editing, setEditing] = useState<Link | null>(null)
  const [qr, setQr] = useState<{ name: string; payload: string } | null>(null)
  const filtered = links.filter((l) => l.name.toLowerCase().includes(q.toLowerCase()) || l.tag.toLowerCase().includes(q.toLowerCase()))

  async function copyLink(value: string) {
    try {
      await navigator.clipboard.writeText(value)
      setNotice('VLESS ссылка скопирована')
    } catch {
      setNotice('Не удалось скопировать в буфер обмена')
    }
  }

  async function action(id: number, type: 'delete' | 'regenerate' | 'toggle' | 'qr') {
    if (type === 'delete') {
      if (!confirm('Удалить ссылку? Действие необратимо.')) return
      await apiFetch(`/api/links/${id}`, { method: 'DELETE' })
      setNotice('Ссылка удалена')
    }
    if (type === 'regenerate') {
      await apiFetch(`/api/links/${id}/regenerate`, { method: 'POST' })
      setNotice('UUID успешно обновлен')
    }
    if (type === 'toggle') {
      const link = links.find((i) => i.id === id)
      if (!link) return
      await apiFetch(`/api/links/${id}`, { method: 'PATCH', body: JSON.stringify({ enabled: !link.enabled }) })
      setNotice(link.enabled ? 'Ссылка отключена' : 'Ссылка включена')
    }
    if (type === 'qr') {
      const response = await apiFetch<{ qr_payload: string; link_name: string }>(`/api/links/${id}/qr`)
      setQr({ name: response.link_name, payload: response.qr_payload })
      return
    }
    await reload()
  }

  return (
    <Card>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2"><SectionTitle title="VLESS ссылки" subtitle="Поиск, управление и контроль лимитов" /><div className="flex w-full gap-2 sm:w-auto"><Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Поиск по имени или тегу" className="sm:w-72" /><Button onClick={onCreate}>Создать</Button></div></div>
      {filtered.length === 0 ? <EmptyState title="Ссылки не найдены" subtitle="Проверьте фильтр или создайте новую ссылку." /> : <div className="max-h-[62vh] overflow-auto"><table className="w-full min-w-[860px] text-sm"><thead className="sticky top-0 bg-panel"><tr className="text-left text-muted"><th className="py-2">Имя</th><th>Статус</th><th>IP</th><th>Активность</th><th>Трафик</th><th>Лимит / Срок</th><th>Действия</th></tr></thead><tbody>{filtered.map((l) => <tr key={l.id} className="border-t border-border align-top hover:bg-bg/60"><td className="py-3"><p>{l.name}</p><p className="text-xs text-muted">{l.tag || 'Без тега'}</p></td><td><div className="flex flex-wrap gap-1"><Badge tone={toneByStatus(l.status) as any}>{statusLabel[l.status] ?? l.status}</Badge>{l.traffic_limit_gb && l.total_traffic_gb / l.traffic_limit_gb > 0.8 && <Badge tone="warn">Лимит &gt; 80%</Badge>}</div></td><td className="font-['JetBrains_Mono'] text-xs">{l.last_ip ?? '—'}</td><td>{formatDate(l.last_activity_at)}</td><td>{formatTraffic(l.total_traffic_gb)}</td><td>{l.traffic_limit_gb ? `${l.traffic_limit_gb} GB` : '—'} / {l.expires_at ? formatDate(l.expires_at) : '—'}</td><td><div className="flex flex-wrap gap-1"><Button variant="secondary" onClick={() => copyLink(l.vless_url)}>Copy</Button><Button variant="secondary" onClick={() => action(l.id, 'qr')}>QR</Button><Button variant="secondary" onClick={() => setEditing(l)}>Edit</Button><Button variant="secondary" onClick={() => action(l.id, 'regenerate')}>UUID</Button><Button variant="secondary" onClick={() => action(l.id, 'toggle')}>{l.enabled ? 'Off' : 'On'}</Button><Button variant="danger" onClick={() => action(l.id, 'delete')}>Del</Button></div></td></tr>)}</tbody></table></div>}
      <EditLinkModal link={editing} onOpenChange={(open) => !open && setEditing(null)} onDone={() => { setNotice('Изменения сохранены'); return reload() }} />
      <Modal open={Boolean(qr)} onOpenChange={(open) => !open && setQr(null)} title={`QR-представление / ${qr?.name ?? ''}`}><p className="mb-2 text-sm text-muted">Скопируйте строку ниже и сгенерируйте QR-код в VPN-клиенте.</p><pre className="overflow-auto rounded-xl border border-border bg-bg p-3 text-xs font-['JetBrains_Mono']">{qr?.payload}</pre></Modal>
    </Card>
  )
}

function EditLinkModal({ link, onOpenChange, onDone }: { link: Link | null; onOpenChange: (open: boolean) => void; onDone: () => void }) {
  const [name, setName] = useState('')
  const [tag, setTag] = useState('')
  const [note, setNote] = useState('')

  useEffect(() => {
    setName(link?.name ?? '')
    setTag(link?.tag ?? '')
    setNote(link?.note ?? '')
  }, [link])

  return (
    <Modal open={Boolean(link)} onOpenChange={onOpenChange} title="Редактировать ссылку">
      <div className="grid gap-2">
        <Input placeholder="Имя" value={name} onChange={(e) => setName(e.target.value)} />
        <Input placeholder="Тег" value={tag} onChange={(e) => setTag(e.target.value)} />
        <Input placeholder="Заметка" value={note} onChange={(e) => setNote(e.target.value)} />
        <div className="flex justify-end gap-2"><Button variant="secondary" onClick={() => onOpenChange(false)}>Отмена</Button><Button onClick={async () => { if (!link) return; await apiFetch(`/api/links/${link.id}`, { method: 'PATCH', body: JSON.stringify({ name, tag, note }) }); onOpenChange(false); onDone() }}>Сохранить</Button></div>
      </div>
    </Modal>
  )
}

function ClientsView({ clients }: { clients: Client[] }) {
  const [selectedId, setSelectedId] = useState<number | null>(clients[0]?.id ?? null)
  const selected = clients.find((c) => c.id === selectedId) ?? null

  return (
    <div className="grid gap-3 lg:grid-cols-3">
      <Card className="lg:col-span-1">
        <SectionTitle title="Список клиентов" subtitle="Выберите клиента для детального просмотра" />
        <div className="space-y-2">{clients.map((c) => <button key={c.id} onClick={() => setSelectedId(c.id)} className={cn('w-full rounded-xl border p-3 text-left transition', selectedId === c.id ? 'border-indigo-400 bg-indigo-500/10' : 'border-border bg-bg hover:border-indigo-300/60')}><div className="flex items-center justify-between"><span>{c.client_name}</span><Badge tone={c.status === 'active' ? 'success' : 'default'}>{statusLabel[c.status] ?? c.status}</Badge></div><p className="mt-1 text-xs text-muted">{c.link_name}</p></button>)}</div>
      </Card>
      <Card className="lg:col-span-2">
        {!selected ? <EmptyState title="Клиент не выбран" subtitle="Выберите клиента слева, чтобы увидеть детали." /> : <><SectionTitle title="Детали клиента" subtitle="Текущая активность, IP-история и события" /><div className="grid gap-3 sm:grid-cols-2"><div className="rounded-xl border border-border bg-bg p-3"><p className="text-xs text-muted">Имя</p><p>{selected.client_name}</p><p className="mt-2 text-xs text-muted">Линк</p><p>{selected.link_name}</p><p className="mt-2 text-xs text-muted">Статус</p><Badge tone={selected.status === 'active' ? 'success' : 'default'}>{statusLabel[selected.status] ?? selected.status}</Badge></div><div className="rounded-xl border border-border bg-bg p-3"><p className="text-xs text-muted">Текущий IP</p><p className="font-['JetBrains_Mono'] text-sm">{selected.current_ip}</p><p className="mt-2 text-xs text-muted">История IP</p><p className="font-['JetBrains_Mono'] text-xs text-slate-300">{selected.ip_history.join(' • ') || '—'}</p></div></div><div className="mt-3 rounded-xl border border-border bg-bg p-3"><p className="text-xs text-muted">Трафик и сессии</p><p className="text-sm">Сессий: {selected.active_sessions} • 24ч: {formatTraffic(selected.traffic_24h_gb)} • 7д: {formatTraffic(selected.traffic_7d_gb)} • Всего: {formatTraffic(selected.total_traffic_gb)}</p><p className="mt-1 text-xs text-muted">Заметка: {selected.note || '—'} • Тег: {selected.tag || '—'}</p></div><div className="mt-3"><p className="mb-2 text-xs text-muted">Последние события</p><div className="flex flex-wrap gap-2">{selected.events.length ? selected.events.map((e, i) => <Badge key={i} tone={e.type === 'suspicious' ? 'warn' : 'info'}>{e.label} • {e.time}</Badge>) : <Badge>Событий нет</Badge>}</div></div></>}
      </Card>
    </div>
  )
}

function SettingsView({ server, logs }: { server: ServerStatus | null; logs: LogItem[] }) {
  const [serverLogs, setServerLogs] = useState<string[]>([])
  useEffect(() => {
    apiFetch<{ lines: string[] }>('/api/server/logs').then((x) => setServerLogs(x.lines)).catch(() => setServerLogs([]))
  }, [])

  return (
    <div className="grid gap-3 lg:grid-cols-2">
      <Card>
        <SectionTitle title="Состояние сервера" subtitle="Основные параметры Xray на текущем хосте" />
        <div className="grid gap-2 sm:grid-cols-2">
          <div className="rounded-xl border border-border bg-bg p-3"><p className="text-xs text-muted">Статус</p><Badge tone={toneByStatus(server?.service_status) as any}>{statusLabel[server?.service_status ?? ''] ?? server?.service_status ?? 'unknown'}</Badge></div>
          <div className="rounded-xl border border-border bg-bg p-3"><p className="text-xs text-muted">Версия Xray</p><p>{server?.xray_version ?? '—'}</p></div>
          <div className="rounded-xl border border-border bg-bg p-3"><p className="text-xs text-muted">Uptime</p><p>{server?.uptime_hours ?? 0} часов</p></div>
          <div className="rounded-xl border border-border bg-bg p-3"><p className="text-xs text-muted">Адрес</p><p>{server?.domain ?? '—'}:{server?.port ?? '—'}</p></div>
        </div>
        <div className="mt-3 rounded-xl border border-border bg-bg p-3"><p className="mb-1 text-xs text-muted">Сводка окружения</p><pre className="text-xs text-slate-300">{JSON.stringify(server?.config_summary ?? {}, null, 2)}</pre></div>
      </Card>
      <Card>
        <SectionTitle title="Логи и активность" subtitle="Живые логи Xray и аудит администратора" />
        <div className="rounded-xl border border-border bg-bg p-3 font-['JetBrains_Mono'] text-xs">{serverLogs.length === 0 ? <p className="font-['Inter'] text-muted">Логи временно недоступны</p> : serverLogs.map((l, i) => <p key={i} className="mb-1">{l}</p>)}</div>
        <p className="mb-2 mt-3 text-xs text-muted">Журнал администратора</p>
        <div className="max-h-44 space-y-1 overflow-auto rounded-xl border border-border bg-bg p-3 text-sm">{logs.length ? logs.map((l) => <p key={l.id}><span className="text-muted">{formatDate(l.created_at)}</span> — {l.action}</p>) : <p className="text-muted">Пока пусто</p>}</div>
      </Card>
    </div>
  )
}

function CreateLinkModal({ open, onOpenChange, onDone }: { open: boolean; onOpenChange: (v: boolean) => void; onDone: () => void }) {
  const [name, setName] = useState('')
  const [tag, setTag] = useState('Test device')
  const [note, setNote] = useState('')
  const [limit, setLimit] = useState('40')
  const [expires, setExpires] = useState('')

  return (
    <Modal open={open} onOpenChange={onOpenChange} title="Создать VLESS ссылку">
      <div className="grid gap-2">
        <Input placeholder="Имя" value={name} onChange={(e) => setName(e.target.value)} />
        <Input placeholder="Тег" value={tag} onChange={(e) => setTag(e.target.value)} />
        <Input placeholder="Заметка" value={note} onChange={(e) => setNote(e.target.value)} />
        <Input placeholder="Лимит GB" value={limit} onChange={(e) => setLimit(e.target.value)} />
        <Input type="date" value={expires} onChange={(e) => setExpires(e.target.value)} />
        <div className="flex justify-end gap-2"><Button variant="secondary" onClick={() => onOpenChange(false)}>Отмена</Button><Button onClick={async () => { await apiFetch('/api/links', { method: 'POST', body: JSON.stringify({ name, tag, note: note || 'Создано из UI', traffic_limit_gb: Number(limit), expires_at: expires ? new Date(expires).toISOString() : null, enabled: true }) }); setName(''); setTag('Test device'); setNote(''); setLimit('40'); setExpires(''); onOpenChange(false); onDone() }}>Создать</Button></div>
      </div>
    </Modal>
  )
}
