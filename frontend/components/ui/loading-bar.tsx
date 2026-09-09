import { cn } from '@/lib/utils'

export function LoadingBar({
  className,
  label = 'Processing',
}: {
  className?: string
  label?: string
}) {
  return (
    <div
      role="progressbar"
      aria-label={label}
      className={cn(
        'relative h-1 w-full overflow-hidden rounded-full bg-[#b1b4b6]',
        className
      )}
    >
      <div className="animate-indeterminate absolute inset-y-0 left-0 w-2/5 rounded-full bg-[var(--govuk-brand-colour)]" />
    </div>
  )
}
