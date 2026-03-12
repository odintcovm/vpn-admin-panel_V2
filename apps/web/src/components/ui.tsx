import React from 'react'
import * as Dialog from '@radix-ui/react-dialog'
import { cn } from '../lib/utils'

type ButtonVariant = 'primary' | 'secondary' | 'danger' | 'ghost'

export function Card({ className, children }: React.PropsWithChildren<{ className?: string }>) {
  return <div className={cn('rounded-2xl border border-border/90 bg-panel p-4 shadow-soft', className)}>{children}</div>
}

export function SectionTitle({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="mb-3">
      <h3 className="text-base font-semibold text-slate-100">{title}</h3>
      {subtitle && <p className="text-sm text-muted">{subtitle}</p>}
    </div>
  )
}

export function Badge({ children, tone = 'default' }: React.PropsWithChildren<{ tone?: 'default' | 'success' | 'warn' | 'danger' | 'info' }>) {
  const map = {
    default: 'bg-slate-700/40 text-slate-200 border border-slate-500/20',
    success: 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30',
    warn: 'bg-amber-500/15 text-amber-300 border border-amber-500/30',
    danger: 'bg-rose-500/15 text-rose-300 border border-rose-500/30',
    info: 'bg-indigo-500/15 text-indigo-300 border border-indigo-400/30'
  }
  return <span className={cn('inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium', map[tone])}>{children}</span>
}

export function Button({ className, variant = 'primary', ...props }: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: ButtonVariant }) {
  const style = {
    primary: 'bg-indigo-500 text-white hover:bg-indigo-400',
    secondary: 'bg-slate-700/70 text-slate-100 hover:bg-slate-600',
    danger: 'bg-rose-600 text-white hover:bg-rose-500',
    ghost: 'bg-transparent text-slate-200 hover:bg-slate-700/40'
  }
  return <button className={cn('min-h-9 rounded-xl px-3 py-2 text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-400/60 disabled:opacity-50', style[variant], className)} {...props} />
}

export function Input(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={cn('min-h-10 w-full rounded-xl border border-border bg-bg px-3 py-2 text-sm text-slate-100 placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-indigo-400/60', props.className)} />
}

export function RetryAction({ onRetry }: { onRetry: () => void }) {
  return <Button variant="secondary" onClick={onRetry}>Повторить</Button>
}

export function InlineNotice({ tone = 'info', text }: { tone?: 'info' | 'warn' | 'danger'; text: string }) {
  const map = { info: 'border-indigo-400/40 text-indigo-200', warn: 'border-amber-400/40 text-amber-200', danger: 'border-rose-500/40 text-rose-200' }
  return <Card className={map[tone]}>{text}</Card>
}

export function LoadingState({ text = 'Загрузка данных...' }: { text?: string }) {
  return <Card className="text-muted">{text}</Card>
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return <Card className="border-rose-500/40 text-rose-200"><div className="flex items-center justify-between gap-3"><span>{message}</span>{onRetry && <RetryAction onRetry={onRetry} />}</div></Card>
}

export function SkeletonBlock({ rows = 4 }: { rows?: number }) {
  return <Card>{Array.from({ length: rows }).map((_, i) => <div key={i} className="mb-2 h-4 animate-pulse rounded bg-slate-700/60" />)}</Card>
}

export function EmptyState({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <div className="rounded-xl border border-dashed border-border bg-bg/60 p-6 text-center">
      <p className="font-medium text-slate-200">{title}</p>
      <p className="mt-1 text-sm text-muted">{subtitle}</p>
    </div>
  )
}

export function Modal({ open, onOpenChange, title, children }: React.PropsWithChildren<{ open: boolean; onOpenChange: (v: boolean) => void; title: string }>) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/60 backdrop-blur-[2px]" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-20 w-[92vw] max-w-xl -translate-x-1/2 -translate-y-1/2 rounded-2xl border border-border bg-panel p-6 shadow-soft">
          <Dialog.Title className="mb-3 text-lg font-semibold text-slate-100">{title}</Dialog.Title>
          {children}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
