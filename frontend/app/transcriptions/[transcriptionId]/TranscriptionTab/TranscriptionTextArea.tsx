import { DialogueEntryForm } from '@/types/transcriptions'
import posthog from 'posthog-js'
import { useEffect, useRef, useState } from 'react'
import { Control, Controller } from 'react-hook-form'

export const TranscriptionTextArea = ({
  index,
  control,
}: {
  index: number
  control: Control<DialogueEntryForm>
}) => {
  const [isEditing, setIsEditing] = useState(false)
  const textRef = useRef<HTMLParagraphElement>(null)

  useEffect(() => {
    const target = textRef.current
    if (!isEditing || !target) return
    target.focus()
    // focus() alone doesn't create a caret when the element was
    // already focused (keyboard Enter), so place one at the end
    const selection = window.getSelection()
    if (selection) {
      const range = document.createRange()
      range.selectNodeContents(target)
      range.collapse(false)
      selection.removeAllRanges()
      selection.addRange(range)
    }
  }, [isEditing])

  return (
    <div className="flex-1">
      <Controller
        render={({ field: { onChange, ...field } }) => {
          const commit = () => {
            const target = textRef.current
            if (!target) return
            const newText = target.innerText.trim()
            if (newText !== field.value) {
              onChange(newText)

              posthog.capture('transcript_text_edited', {
                entry_index: index,
              })
            }
            setIsEditing(false)
          }

          const cancel = () => {
            const target = textRef.current
            if (target) {
              target.innerText = field.value ?? ''
            }
            setIsEditing(false)
          }

          return (
            <p
              ref={textRef}
              className="transcription-text-area__text-box"
              id={`transcription-text-area-${index}`}
              tabIndex={0}
              role="textbox"
              aria-multiline="true"
              aria-readonly={!isEditing}
              aria-label={
                isEditing
                  ? `Editing transcript, entry ${index + 1}. Press Enter to save or Escape to cancel`
                  : `Edit transcript, entry ${index + 1}. Press Enter to start editing`
              }
              contentEditable={isEditing}
              suppressContentEditableWarning
              onClick={() => setIsEditing(true)}
              onBlur={() => {
                if (isEditing) {
                  commit()
                }
              }}
              onKeyDown={(e) => {
                if (e.key === 'Escape' && isEditing) {
                  e.preventDefault()
                  cancel()
                  return
                }
                if (e.key !== 'Enter' || e.shiftKey) return
                e.preventDefault()
                if (isEditing) {
                  commit()
                } else {
                  setIsEditing(true)
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
