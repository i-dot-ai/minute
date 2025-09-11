import { DialogueEntryForm } from '@/app/transcriptions/[transcriptionId]/TranscriptionTab/TranscriptionTab'
import posthog from 'posthog-js'
import { Control, Controller } from 'react-hook-form'

export const TranscriptionTextArea = ({
  index,
  control,
}: {
  index: number
  control: Control<DialogueEntryForm>
}) => {
  return (
    <div className="flex-1">
      <Controller
        render={({ field: { onChange, ...field } }) => (
          <p
            className="flex-1 cursor-text rounded px-2 transition-all hover:bg-gray-100 hover:shadow-sm"
            onClick={(e) => {
              const target = e.target as HTMLParagraphElement
              if (target.getAttribute('contenteditable') !== 'true') {
                target.setAttribute('contenteditable', 'true')
                target.focus()
              }
            }}
            onBlur={(e) => {
              const target = e.target as HTMLParagraphElement
              target.setAttribute('contenteditable', 'false')
              const newText = target.innerText.trim()

              if (newText !== field.value) {
                onChange(newText)

                posthog.capture('transcript_text_edited', {
                  entry_index: index,
                })
              }
            }}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                e.currentTarget.blur()
              }
            }}
          >
            {field.value}
          </p>
        )}
        control={control}
        name={`entries.${index}.text`}
      />
    </div>
  )
}
