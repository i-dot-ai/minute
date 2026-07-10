import { DialogueEntryForm } from '@/types/transcriptions'
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
        render={({ field: { onChange, ...field } }) => {
          const startEditing = (target: HTMLParagraphElement) => {
            if (target.getAttribute('contenteditable') !== 'true') {
              target.setAttribute('contenteditable', 'true')
              target.focus()
            }
          }
          return (
            <p
              className="transcription-text-area__text-box"
              id={`transcription-text-area-${index}`}
              tabIndex={0}
              role="textbox"
              aria-label={`Edit transcript, entry ${index + 1}. Press Enter to start editing`}
              onClick={(e) => startEditing(e.target as HTMLParagraphElement)}
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
                if (e.key !== 'Enter' || e.shiftKey) return
                e.preventDefault()
                const target = e.currentTarget
                if (target.getAttribute('contenteditable') !== 'true') {
                  startEditing(target)
                } else {
                  target.blur()
                }
              }}
            >
              {field.value}
            </p>
          )
        }}
        control={control}
        name={`entries.${index}.text`}
      />
    </div>
  )
}
