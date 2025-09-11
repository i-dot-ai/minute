import { DataRetentionNotice } from '@/components/layout/DataRententionNotice'
import { PosthogBanner } from '@/components/posthog-banner'
import { PaginatedTranscriptions } from '@/components/recent-meetings/paginated-transcriptions'
import { Button } from '@/components/ui/button'
import { Plus } from 'lucide-react'
import Link from 'next/link'

export default function Home() {
  return (
    <div className="mx-auto max-w-3xl">
      <DataRetentionNotice />
      <PosthogBanner />
      <div className="mb-4">
        <h1 className="mb-4 text-4xl font-bold">
          AI transcription and drafting service
        </h1>
        <p className="text-slate-600">
          Transcribe and summarise your meetings with AI. Click the New Meeting
          button below to begin. Suitable up to{' '}
          <span className="font-bold">OFFICIAL SENSITIVE</span>.
        </p>
      </div>
      <Button
        className="mb-6 w-full bg-blue-500 p-6 hover:bg-blue-800 active:bg-amber-400"
        asChild
      >
        <Link href="/new">
          <Plus />
          New meeting
        </Link>
      </Button>
      <PaginatedTranscriptions />
    </div>
  )
}
