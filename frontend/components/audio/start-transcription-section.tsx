import { TranscriptionForm } from '@/components/audio/types'
import { TemplateSelect } from '@/components/template-radio-group'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { TemplateMetadata } from '@/lib/client'
import { Loader2 } from 'lucide-react'
import { Controller, useFormContext } from 'react-hook-form'

export const StartTranscriptionSection = ({
  isShowing,
  isPending,
  templates,
  isLoadingTemplates,
  selectedTemplate,
}: {
  isShowing: boolean
  isPending: boolean
  templates: TemplateMetadata[]
  isLoadingTemplates: boolean
  selectedTemplate: TemplateMetadata | undefined
}) => {
  const form = useFormContext<TranscriptionForm>()
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
          <TemplateSelect
            value={value}
            onChange={onChange}
            templates={templates}
            isLoading={isLoadingTemplates}
          />
        )}
      />
      {selectedTemplate && selectedTemplate.agenda_usage != 'not_used' && (
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
