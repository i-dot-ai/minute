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
            className="transcription-text-area__text-box"
            id={`transcription-text-area-${index}`}
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
