import { LoadingBar } from '@/components/ui/loading-bar'
import { cn } from '@/lib/utils'
import { RefreshCw } from 'lucide-react'

export function ProcessingCard({
  heading,
  estimatedMinutes,
  isStalled = false,
  className,
}: {
  heading: string
  estimatedMinutes?: number | null
  isStalled?: boolean
  className?: string
}) {
  return (
    <div
      role="status"
      className={cn(
        'govuk-!-padding-5 govuk-!-padding-top-8 bg-(--govuk-surface-background-colour)',
        className
      )}
    >
      <div className="govuk-!-margin-bottom-6 inline-flex items-center gap-2">
        <RefreshCw className="size-4 animate-spin text-(--govuk-text-colour)" />
        <h2 className="govuk-heading-m govuk-!-margin-bottom-0">{heading}</h2>
      </div>

      {isStalled ? (
        <div className="govuk-warning-text">
          <span className="govuk-warning-text__icon" aria-hidden="true">
            !
          </span>
          <strong className="govuk-warning-text__text">
            <span className="govuk-visually-hidden">Warning</span>
            Taking longer than usual. Leave this page if needed, it will
            continue in the background.
          </strong>
        </div>
      ) : (
        !!estimatedMinutes && (
          <p className="govuk-body">
            Estimated time to complete:{' '}
            <strong>
              {estimatedMinutes} {estimatedMinutes === 1 ? 'minute' : 'minutes'}
            </strong>
          </p>
        )
      )}
      <div className="govuk-!-margin-bottom-7 govuk-!-margin-top-6">
        <LoadingBar />
      </div>
    </div>
  )
}
