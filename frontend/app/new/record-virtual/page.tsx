import { TabRecorderForm } from '@/components/audio/tab-recorder/tab-recorder'

export default function RecordAudio() {
  return (
    <div>
      <h1 className="mb-6 text-3xl font-bold">Record a meeting</h1>
      <TabRecorderForm />
    </div>
  )
}
