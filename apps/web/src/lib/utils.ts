import { clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: Array<string | false | null | undefined>) {
  return twMerge(clsx(inputs))
}

export const apiBase = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
export const apiToken = import.meta.env.VITE_API_TOKEN ?? 'admin-token'

export type ApiError = {
  status: number
  code: string
  message: string
  details?: unknown
}

export async function parseApiError(res: Response): Promise<ApiError> {
  const text = await res.text()
  try {
    const parsed = JSON.parse(text)
    const detailError = parsed?.detail?.error
    const rootError = parsed?.error

    return {
      status: res.status,
      code: detailError?.code ?? rootError?.code ?? `HTTP_${res.status}`,
      message: detailError?.message ?? rootError?.message ?? parsed?.detail ?? text,
      details: detailError?.details ?? rootError?.details
    }
  } catch {
    return { status: res.status, code: `HTTP_${res.status}`, message: text || 'Unknown API error' }
  }
}

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
    const err = await parseApiError(res)
    throw new Error(`${err.code}: ${err.message}`)
  }

  return res.json()
}
