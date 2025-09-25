import { TranscriptionForm } from '@/components/audio/types'
import { TemplateSelect } from '@/components/template-select/template-select'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
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
  // Fetch templates from API

  if (!isShowing) {
    return null
  }
  return (
    <div className="mt-4 flex flex-col gap-2">
      <Button
        type="submit"
        className="w-full bg-blue-500 hover:bg-blue-800 active:bg-yellow-400"
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
      </Button>
      <Controller
        control={form.control}
        name="template"
        render={({ field: { value, onChange } }) => (
          <TemplateSelect value={value} onChange={onChange} />
        )}
      />
      {selectedTemplate.agenda_usage != 'not_used' && (
        <div className="mb-4 rounded">
          <h3 className="text-semibold m">
            Agenda (
            {selectedTemplate.agenda_usage == 'optional'
              ? 'optional'
              : 'required'}
            ):
          </h3>
          <p className="text-muted-foreground text-sm">
            Add discussion points from the meeting that should be included in
            the summary.
          </p>
          <Textarea
            className="bg-white"
            placeholder={`Agenda item 1
Agenda item 2
Agenda item 3
...`}
            {...form.register('agenda', {
              required: selectedTemplate.agenda_usage == 'required',
            })}
          />
        </div>
      )}
    </div>
  )
}
