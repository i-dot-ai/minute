import { AudioUploadForm } from '@/components/audio/AudioUploadForm'
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
      <h1 className="text-3xl font-bold">Upload a file</h1>
      <AudioUploadForm />
    </div>
  )
}
