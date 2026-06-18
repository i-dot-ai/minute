'use client'

import { useGovukModule } from '@/hooks/use-govuk-module'
import { useStartTranscription } from '@/hooks/useStartTranscription'
import { useEffect, useRef, useState } from 'react'
import { FormProvider } from 'react-hook-form'
import { StartTranscriptionSection } from './start-transcription-section'

export const AudioUploadForm = () => {
  const { isPending, onSubmit, form } = useStartTranscription()
  const [fileError, setFileError] = useState<string | null>(null)
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
      if (!selected.type.startsWith('audio/') && !selected.type.startsWith('video/')) {
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
    <>
      <FormProvider {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)}>
          <div className={`govuk-form-group${fileError ? ' govuk-form-group--error' : ''}`}>
            <label className="govuk-label govuk-fieldset__legend--l" htmlFor="file-upload" id="file-upload-label">
              Select a file to upload
            </label>

            <div id="file-upload-hint" className="govuk-hint">
              Maximum file size: 5GB. Please ensure that all participants are aware that they have been recorded.
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
          </div>
          <StartTranscriptionSection isShowing={!!file} isPending={isPending} />
        </form>
      </FormProvider>
    </>
  )
}
