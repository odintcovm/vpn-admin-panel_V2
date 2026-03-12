import { clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: Array<string | false | null | undefined>) {
  return twMerge(clsx(inputs))
}

export const apiBase = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
export const apiToken = import.meta.env.VITE_API_TOKEN ?? 'admin-token'

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers)
  headers.set('x-api-token', apiToken)
  if (init?.body) {
    headers.set('Content-Type', 'application/json')
  }

  const res = await fetch(`${apiBase}${path}`, {
    ...init,
    headers
  })

  if (!res.ok) {
    const text = await res.text()
    throw new Error(`API error ${res.status}: ${text}`)
  }

  return res.json()
}
