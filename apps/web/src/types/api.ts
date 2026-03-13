export type DashboardOverview = {
  total_links: number
  active_connections: number
  traffic_24h_gb: number
  server_status: string
  chart_24h: { label: string; value: number }[]
  chart_7d: { label: string; value: number }[]
}

export type Link = {
  id: number
  name: string
  uuid: string
  note: string
  tag: string
  status: string
  enabled: boolean
  last_ip: string | null
  last_activity_at: string | null
  total_traffic_gb: number
  traffic_limit_gb: number | null
  expires_at: string | null
  vless_url: string
}

export type Client = {
  id: number
  client_name: string
  link_name: string
  link_id: number
  status: string
  current_ip: string
  ip_history: string[]
  active_sessions: number
  total_traffic_gb: number
  traffic_24h_gb: number
  traffic_7d_gb: number
  last_activity_at: string | null
  note: string
  tag: string
  events: { type: string; label: string; time: string }[]
}


export type ClientProfileFormat = {
  key: string
  title: string
  available: boolean
  description: string
}

export type ClientProfiles = {
  link_id: number
  link_name: string
  formats: ClientProfileFormat[]
}

export type ClientProfilePayload = {
  key: string
  title: string
  content_type: string
  filename?: string | null
  payload: string
  instruction: string
}

export type SessionItem = {
  id: number
  client_name: string
  link_name: string
  source_ip: string
  status: string
  started_at: string
  duration_sec: number
  inbound_gb: number
  outbound_gb: number
}

export type SessionDrilldown = SessionItem & {
  reconnect_summary: string
  related_events: { title: string; message: string; level: string; created_at: string }[]
}

export type TimelineEvent = {
  at: string
  kind: string
  title: string
  message: string
}

export type HealthFreshness = {
  provider_status: 'healthy' | 'degraded' | 'disconnected'
  backend_status: 'ok' | 'degraded' | 'error'
  server_status: string
  last_success_refresh_at: string
  data_freshness_sec: number
}

export type NotificationItem = {
  id: number
  severity: string
  title: string
  message: string
  entity_type: string | null
  entity_id: string | null
  is_read: boolean
  read_at?: string | null
  created_at: string
}

export type AuthMe = {
  subject_id: string
  role: string
  permissions: string[]
  auth_mode: string
  user_id?: number | null
  dev_role_emulation_enabled: boolean
}

export type ActionExecuteIn = {
  action: 'restart' | 'reload' | 'regenerate_uuid' | 'set_link_enabled' | 'mark_suspicious'
  target_type: 'server' | 'link' | 'client'
  target_id?: number
  reason?: string
  enabled?: boolean
}

export type ActionExecuteOut = {
  ok: boolean
  action: string
  result: string
  at: string
}

export type ServerStatus = {
  service_status: string
  xray_version: string
  uptime_hours: number
  hostname: string
  domain: string
  port: number
  config_summary: Record<string, unknown>
}

export type Overview = DashboardOverview


export type ProviderList = {
  active_provider: string
  items: { name: string; active: boolean; capabilities: Record<string, boolean> }[]
}

export type AuthLoginOut = {
  ok: boolean
  auth_mode: string
  role: string
  subject_id: string
}
