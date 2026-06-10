import { MicRecorderForm } from '@/components/audio/mic-recorder'

export default function RecordAudio() {
  return (
    <>
      <h1 className="govuk-heading-xl">Record a meeting</h1>
      <MicRecorderForm />
    </>
  )
}
