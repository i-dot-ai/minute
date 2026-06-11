import { AudioUploadForm } from '@/components/audio/AudioUploadForm'

export default function RecordAudio() {
  return (
    <div className="govuk-grid-row">
      <div className="govuk-grid-column-two-thirds">
        <h1 className="govuk-heading-xl">Upload a file</h1>
        <AudioUploadForm />
      </div>
    </div>
  )
}
