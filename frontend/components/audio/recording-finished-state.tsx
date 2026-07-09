import { Loader2 } from 'lucide-react'

export function RecordingFinishedState({
  isUploading,
}: {
  isUploading: boolean
}) {
  return (
    <div className="govuk-!-margin-top-4">
      <div className="flex items-center gap-2">
        <Loader2 className="size-5 animate-spin" aria-hidden="true" />
        <p className="govuk-heading-m govuk-!-margin-bottom-0">Recording finished</p>
      </div>
      {isUploading && (
        <p className="govuk-hint govuk-!-margin-top-2 govuk-!-margin-bottom-0">
          Uploading your recording...
        </p>
      )}
    </div>
  )
}
