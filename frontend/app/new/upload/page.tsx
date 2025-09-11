import { AudioUploadForm } from '@/components/audio/AudioUploadForm'

export default function RecordAudio() {
  return (
    <div>
      <h1 className="text-3xl font-bold">Upload a file</h1>
      <AudioUploadForm />
    </div>
  )
}
