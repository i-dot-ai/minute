'use client'

import { useGovukModule } from '@/hooks/use-govuk-module'
import { useStartTranscription } from '@/hooks/useStartTranscription'
import { useRouter } from 'next/navigation'
import { useEffect, useRef, useState } from 'react'
import { FormProvider } from 'react-hook-form'
import { GenerateSummaryDialog } from './generate-summary-dialog'

export const AudioUploadForm = () => {
  const router = useRouter()
  const { isPending, onSubmit, form } = useStartTranscription(undefined, (id) =>
    router.push(`/new/status/${id}`)
  )
  const [fileError, setFileError] = useState<string | null>(null)
  const [open, setOpen] = useState(false)
  const wrapperRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const file = form.watch('file')

  useGovukModule(wrapperRef, 'FileUpload')

  useEffect(() => {
    const input = inputRef.current
    if (!input) return
    const handler = () => {
      const selected = input.files?.[0]
      if (!selected) return
      if (
        !selected.type.startsWith('audio/') &&
        !selected.type.startsWith('video/')
      ) {
        setFileError('The selected file must be an audio or video file')
        input.value = ''
        form.setValue('file', null)
        return
      }
      setFileError(null)
      form.setValue('file', selected)
    }
    input.addEventListener('change', handler)
    return () => input.removeEventListener('change', handler)
  }, [form])

  return (
    <FormProvider {...form}>
      <form
        onSubmit={form.handleSubmit(onSubmit)}
        className="govuk-!-margin-top-7"
      >
        <label
          className="govuk-label govuk-fieldset__legend--s"
          htmlFor="file-upload"
          id="file-upload-label"
        >
          Select a file to upload
        </label>

        <div id="file-upload-hint" className="govuk-hint">
          Maximum file size: 5GB.
        </div>

        {fileError && (
          <p id="file-upload-error" className="govuk-error-message">
            <span className="govuk-visually-hidden">Error:</span>
            {fileError}
          </p>
        )}
        <div
          ref={wrapperRef}
          className="govuk-file-upload-wrapper"
          data-module="govuk-file-upload"
        >
          <input
            ref={inputRef}
            className="govuk-file-upload"
            id="file-upload"
            name="file"
            type="file"
            accept="audio/*,video/*"
            aria-describedby="file-upload-hint file-upload-error"
          />
        </div>

        {file && (
          <button
            type="button"
            className="govuk-button govuk-button--start govuk-!-margin-top-4"
            onClick={() => setOpen(true)}
          >
            Generate summary
            <svg
              className="govuk-button__start-icon"
              xmlns="http://www.w3.org/2000/svg"
              width="17.5"
              height="19"
              viewBox="0 0 33 40"
              aria-hidden="true"
              focusable="false"
            >
              <path fill="currentColor" d="M0 0h13l20 20-20 20H0l20-20z" />
            </svg>
          </button>
        )}

        <GenerateSummaryDialog
          open={open}
          onOpenChange={setOpen}
          onConfirm={form.handleSubmit(onSubmit)}
          disabled={isPending}
        />
      </form>
    </FormProvider>
  )
}
