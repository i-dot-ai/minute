import { Mic, MonitorPlay, Upload } from 'lucide-react'
import Link from 'next/link'

export default function NewTranscriptPage() {
  return (
    <div className="flex flex-col gap-2">
      <Link
        href="/new/upload"
        className="flex items-center gap-2 rounded-xl border p-6 hover:bg-blue-100"
      >
        <div className="rounded bg-blue-200 p-2 text-blue-500">
          <Upload size={25} />
        </div>
        <div>
          <h3 className="text-xl font-bold">Upload file</h3>
          <p className="text-sm text-slate-500">
            Upload a recording from your computer
          </p>
        </div>
      </Link>
      <Link
        href="/new/record-virtual"
        className="flex items-center gap-2 rounded-xl border p-6 hover:bg-blue-100"
      >
        <div className="rounded bg-blue-200 p-2 text-blue-500">
          <MonitorPlay size={25} />
        </div>
        <div>
          <h3 className="text-xl font-bold">Record a virtual meeting</h3>
          <p className="text-sm text-slate-500">
            Record a virtual meeting in another tab
          </p>
        </div>
      </Link>
      <Link
        href="/new/record-audio"
        className="flex items-center gap-2 rounded-xl border p-6 hover:bg-blue-100"
      >
        <div className="rounded bg-blue-200 p-2 text-blue-500">
          <Mic size={25} />
        </div>
        <div>
          <h3 className="text-xl font-bold">Record audio</h3>
          <p className="text-sm text-slate-500">
            Record audio using your microphone
          </p>
        </div>
      </Link>
    </div>
  )
}
