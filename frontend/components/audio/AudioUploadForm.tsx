'use client'

import { TranscriptionForm } from '@/components/audio/types'
import { useDefaultTemplate } from '@/hooks/useDefaultTemplate'
import { useGovukModule } from '@/hooks/use-govuk-module'
import { useRecordingSession } from '@/providers/recording-session-provider'
import { Template } from '@/types/templates'
import { useRouter } from 'next/navigation'
import { useEffect, useRef, useState } from 'react'
import { FormProvider, useForm } from 'react-hook-form'
import { GenerateSummaryDialog } from './generate-summary-dialog'

const GENERAL_TEMPLATE: Template = {
  name: 'General',
  description:
    'Standard meeting summary with key points, decisions, and action items',
  agenda_usage: 'optional',
  id: null,
}

export const AudioUploadForm = () => {
  const router = useRouter()
  const { setMode, setUploadFile, setUploadTemplate, setUploadAgenda } =
    useRecordingSession()
  const [fileError, setFileError] = useState<string | null>(null)
  const [open, setOpen] = useState(false)
  const wrapperRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const form = useForm<TranscriptionForm>({
    defaultValues: {
      file: null,
      template: GENERAL_TEMPLATE,
    },
  })
  const file = form.watch('file')
  const selectedTemplate = form.watch('template')
  const agendaValue = form.watch('agenda')
  const agendaRequired =
    typeof selectedTemplate !== 'string' &&
    selectedTemplate?.agenda_usage === 'required'

  const defaultTemplate = useDefaultTemplate()
  useEffect(() => {
    if (defaultTemplate && !form.formState.dirtyFields.template) {
      form.setValue('template', defaultTemplate)
    }
  }, [defaultTemplate, form])

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

  const handleGenerate = () => {
    const values = form.getValues()
    if (!(values.file instanceof File)) return
    setUploadFile(values.file)
    setUploadTemplate(values.template)
    setUploadAgenda(values.agenda)
    setMode('upload-file')
    router.push('/new')
  }

  return (
    <FormProvider {...form}>
      <div className="govuk-!-margin-top-7">
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
            Upload file
          </button>
        )}

        <GenerateSummaryDialog
          open={open}
          onOpenChange={setOpen}
          onConfirm={() => {
            setOpen(false)
            handleGenerate()
          }}
          disabled={agendaRequired && !agendaValue}
        />
      </div>
    </FormProvider>
  )
}
