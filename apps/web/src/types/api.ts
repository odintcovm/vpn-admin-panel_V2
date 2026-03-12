export type Overview = {
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

export type ServerStatus = {
  service_status: string
  xray_version: string
  uptime_hours: number
  hostname: string
  domain: string
  port: number
  config_summary: Record<string, unknown>
}
