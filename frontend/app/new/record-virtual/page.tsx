import { TabRecorderForm } from '@/components/audio/tab-recorder/tab-recorder'
import { Button } from '@/components/ui/button'
import { ChevronLeft } from 'lucide-react'
import Link from 'next/link'

export default function RecordAudio() {
  return (
    <div>
      <Button
        asChild
        variant="link"
        className="mb-4 self-start px-0! underline hover:decoration-2"
      >
        <Link href="/new">
          <span className="flex items-center">
            <ChevronLeft />
            Back
          </span>
        </Link>
      </Button>
      <h1 className="mb-6 text-3xl font-bold">Record a meeting</h1>
      <TabRecorderForm />
    </div>
  )
}
