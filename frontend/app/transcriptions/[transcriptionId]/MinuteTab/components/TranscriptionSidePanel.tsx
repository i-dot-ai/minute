'use client'

import { NewMinuteDialog } from '@/app/transcriptions/[transcriptionId]/MinuteTab/NewMinuteDialog'
import { MinuteListItem } from '@/lib/client'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'

export function TranscriptionSidePanel({
  transcriptionId,
  minutes,
}: {
  transcriptionId: string
  minutes: MinuteListItem[]
}) {
  const pathname = usePathname()
  const router = useRouter()

  return (
    <nav aria-label="Summaries and transcript">
      <ul className="govuk-list govuk-list--spaced">
        <li>
          <Link href="/transcriptions" className="govuk-link govuk-link--no-visited-state">All transcriptions</Link>
        </li>
        <li>
          <h2 className="govuk-heading-s">Summaries</h2>
          <ul className="govuk-list">
            {minutes.map((minute) => {
              const date = new Date(minute.updated_datetime).toLocaleDateString(
                'en-GB',
                {
                  day: 'numeric',
                  month: 'short',
                  year: '2-digit',
                  hour: 'numeric',
                  minute: 'numeric',
                }
              )
              const href = `/transcriptions/${transcriptionId}/summary/${minute.id}`
              const isActive = pathname === href
              return (
                <li key={minute.id}>
                  <Link
                    href={href}
                    className="govuk-link govuk-link--no-visited-state"
                    aria-current={isActive ? 'page' : undefined}
                    style={isActive ? { fontWeight: 'bold' } : undefined}
                  >
                    {minute.template_name} - {date}
                  </Link>
                </li>
              )
            })}
            {minutes.length === 0 && (
              <li className="govuk-body-s">No summaries yet</li>
            )}
          </ul>
          <NewMinuteDialog
            transcriptionId={transcriptionId}
            onCreated={() => router.push(`/transcriptions/${transcriptionId}`)}
          />
        </li>
        <li>
          <h2 className="govuk-heading-s govuk-!-margin-top-4">Transcript</h2>
          <ul className="govuk-list">
            <li>
              <Link
                href={`/transcriptions/${transcriptionId}/transcript`}
                className="govuk-link govuk-link--no-visited-state"
                aria-current={
                  pathname === `/transcriptions/${transcriptionId}/transcript`
                    ? 'page'
                    : undefined
                }
                style={
                  pathname === `/transcriptions/${transcriptionId}/transcript`
                    ? { fontWeight: 'bold' }
                    : undefined
                }
              >
                View transcript
              </Link>
            </li>
          </ul>
        </li>
      </ul>
    </nav>
  )
}
