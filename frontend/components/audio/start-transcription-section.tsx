'use client'

import { TranscriptionForm } from '@/components/audio/types'
import { TemplateSelect } from '@/components/template-select/template-select'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Template } from '@/types/templates'
import { useFormContext } from 'react-hook-form'
import { useState } from 'react'

export const StartTranscriptionSection = ({
  isShowing,
  isPending,
}: {
  isShowing: boolean
  isPending: boolean
}) => {
  const form = useFormContext<TranscriptionForm>()
  const selectedTemplate = form.watch('template')
  const [open, setOpen] = useState(false)
  const [draftTemplate, setDraftTemplate] = useState<Template>(selectedTemplate)

  const handleOpenChange = (nextOpen: boolean) => {
    if (nextOpen) {
      setDraftTemplate(form.getValues('template'))
    }
    setOpen(nextOpen)
  }

  const handleDone = () => {
    form.setValue('template', draftTemplate)
    setOpen(false)
  }

  if (!isShowing) {
    return null
  }
  return (
    <>
      <div className="govuk-grid-row">
        <div className="govuk-grid-column-one-third">
          <h2 className="govuk-heading-m">Selected template:</h2>
          <p className="govuk-body">
            Set the style for your meeting summary
          </p>
        </div>
        <div className="govuk-grid-column-two-thirds">
          <p className="govuk-heading-m govuk-!-margin-bottom-1">
            {selectedTemplate.name}
          </p>
          <p className="govuk-body govuk-!-margin-bottom-4">
            {selectedTemplate.description}
          </p>
          <button
            type="button"
            className="govuk-button govuk-button--secondary govuk-!-margin-bottom-6"
            onClick={() => handleOpenChange(true)}
          >
            Change template
          </button>
        </div>
      </div>


      <Dialog open={open} onOpenChange={handleOpenChange}>
        <DialogContent wideModal>
          <DialogHeader>
            <DialogTitle className="govuk-heading-l">
              Select a template
            </DialogTitle>
          </DialogHeader>
          <TemplateSelect
            value={draftTemplate}
            onChange={setDraftTemplate}
          />
          <DialogFooter>
            <button
              type="button"
              className="govuk-button govuk-button--secondary"
              onClick={() => handleOpenChange(false)}
            >
              Cancel
            </button>
            <button
              type="button"
              className="govuk-button"
              onClick={handleDone}
            >
              Select template
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {selectedTemplate.agenda_usage != 'not_used' && (
        <div className="govuk-grid-row">
          <div className="govuk-form-group">
            <div className="govuk-grid-column-one-third">
              <h3 className="govuk-label-wrapper">
                <label className="govuk-label govuk-label--m" htmlFor="agenda">
                  Agenda (
                  {selectedTemplate.agenda_usage == 'optional'
                    ? 'optional'
                    : 'required'}
                  ):
                </label>
              </h3>
              <div id="agenda-hint" className="govuk-hint">
                Add discussion points from the meeting that should be included in
                the summary.
              </div>
            </div>
            <div className="govuk-grid-column-two-thirds">
              <textarea
                className="govuk-textarea"
                id="agenda"
                rows={4}
                aria-describedby="agenda-hint"
                {...form.register('agenda', {
                  required: selectedTemplate.agenda_usage == 'required',
                })}
              />
            </div>
          </div>
        </div>
      )}
      <div className="govuk-grid-row">
        <div className="govuk-grid-column-one-third">
          <div className="md:p-4"></div>
        </div>
        <div className="govuk-grid-column-two-thirds">
          <button
            type="submit"
            className="govuk-button govuk-button--start"
            disabled={
              isPending ||
              !isShowing ||
              !selectedTemplate ||
              (selectedTemplate.agenda_usage == 'required' && !form.watch('agenda'))
            }
          >
            Generate summary
            <svg className="govuk-button__start-icon" xmlns="http://www.w3.org/2000/svg" width="17.5" height="19" viewBox="0 0 33 40" aria-hidden="true" focusable="false">
              <path fill="currentColor" d="M0 0h13l20 20-20 20H0l20-20z" />
            </svg>
          </button>
          {isPending && (
            <strong className="govuk-tag">
              Uploading...
            </strong>
          )}
        </div>
      </div>
    </>
  )
}
