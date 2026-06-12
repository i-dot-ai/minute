import { DialogueEntryForm } from '@/app/transcriptions/[transcriptionId]/TranscriptionTab/TranscriptionTab'
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
          <textarea
            className="transcription-text-area__text-box"
            value={field.value}
            onChange={onChange}
            id={`transcription-text-area-${index}`}
          />
        )}
        control={control}
        name={`entries.${index}.text`}
      />
    </div>
  )
}
