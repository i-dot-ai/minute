import { TranscriptionForm } from '@/components/audio/types'
import { TemplateSelect } from '@/components/template-select/template-select'
import { Loader2 } from 'lucide-react'
import { Controller, useFormContext } from 'react-hook-form'

export const StartTranscriptionSection = ({
  isShowing,
  isPending,
}: {
  isShowing: boolean
  isPending: boolean
}) => {
  const form = useFormContext<TranscriptionForm>()
  const selectedTemplate = form.watch('template')

  if (!isShowing) {
    return null
  }
  return (
    <div>
      <h2 className="govuk-heading-l">Select a template</h2>
      <Controller
        control={form.control}
        name="template"
        render={({ field: { value, onChange } }) => (
          <TemplateSelect value={value} onChange={onChange} />
        )}
      />
      {selectedTemplate.agenda_usage != 'not_used' && (
        <div>
          <div className="govuk-form-group">
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
            <textarea
              className="govuk-textarea"
              id="agenda"
              rows={5}
              aria-describedby="agenda-hint"
              {...form.register('agenda', {
                required: selectedTemplate.agenda_usage == 'required',
              })}
            />
          </div>
        </div>
      )}
      <button
        type="submit"
        className="govuk-button"
        disabled={
          isPending ||
          !isShowing ||
          !selectedTemplate ||
          (selectedTemplate.agenda_usage == 'required' && !form.watch('agenda'))
        }
      >
        {isPending ? (
          <>
            <Loader2 className="animate-spin" /> Uploading
          </>
        ) : (
          'Upload'
        )}
      </button>
    </div>
  )
}
