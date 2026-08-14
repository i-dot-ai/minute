'use client'

import { NewMinuteDialog } from '@/app/transcriptions/[transcriptionId]/MinuteTab/NewMinuteDialog'
import {
  getTranscriptionTranscriptionsTranscriptionIdGetOptions,
  listMinutesForTranscriptionTranscriptionTranscriptionIdMinutesGetOptions,
} from '@/lib/client/@tanstack/react-query.gen'
import { useQuery } from '@tanstack/react-query'
import Link from 'next/link'
import { useParams, usePathname, useRouter } from 'next/navigation'
import { useState } from 'react'

export function TranscriptionSidePanel() {
  const { transcriptionId } = useParams<{ transcriptionId?: string }>()
  const [menuOpen, setMenuOpen] = useState(false)
  const router = useRouter()
  const pathname = usePathname()
  const { data: minutes = [] } = useQuery({
    ...listMinutesForTranscriptionTranscriptionTranscriptionIdMinutesGetOptions(
      {
        path: { transcription_id: transcriptionId ?? '' },
      }
    ),
    enabled: !!transcriptionId,
  })
  const { data: transcription } = useQuery({
    ...getTranscriptionTranscriptionsTranscriptionIdGetOptions({
      path: { transcription_id: transcriptionId ?? '' },
    }),
    enabled: !!transcriptionId,
  })
  const transcriptPage = !pathname.includes('/summary')

  if (!transcriptionId) return null

  return (
    <div className="govuk-!-padding-top-4 govuk-!-padding-right-6 govuk-!-padding-left-6 overflow-y-auto border-r border-(--govuk-border-colour) bg-white">
      <nav aria-label="Summaries and transcript" className="secondary-nav">
        <ul className="govuk-list govuk-list--spaced flex flex-row md:block">
          <li
            id="tour-summaries"
            className={`flex-1 border-l-4 border-[transparent] pl-4 ${!transcriptPage ? '!border-(--govuk-link-colour)' : ''}`}
          >
            {transcriptPage || minutes.length <= 1 ? (
              <Link
                href={`/transcriptions/${transcriptionId}/summary`}
                className={`govuk-link govuk-link--no-visited-state govuk-link--no-underline ${!transcriptPage ? 'govuk-!-font-weight-bold' : ''}`}
              >
                {minutes.length > 1 ? 'Summaries' : 'Summary'}
              </Link>
            ) : (
              <>
                <h2 className="govuk-caption-s font-normal text-(--govuk-link-colour)">
                  Summaries
                </h2>
                <button
                  type="button"
                  className="govuk-service-navigation__toggle md:!hidden"
                  aria-controls="summaries-nav"
                  aria-expanded={menuOpen}
                  onClick={() => setMenuOpen((open) => !open)}
                >
                  {menuOpen ? 'Hide' : 'Show'} all
                </button>
                <ul
                  className={`govuk-list !pl-[20px] ${menuOpen ? '' : 'max-md:hidden'}`}
                >
                  {minutes.map((minute) => {
                    const date = new Date(
                      minute.updated_datetime
                    ).toLocaleDateString('en-GB', {
                      day: 'numeric',
                      month: 'short',
                      year: '2-digit',
                      hour: 'numeric',
                      minute: 'numeric',
                    })
                    const href = `/transcriptions/${transcriptionId}/summary/${minute.id}`
                    const isActive = pathname === href
                    return (
                      <li
                        key={minute.id}
                        className="before:ml-[-20px] before:text-[#484949] before:content-['—']"
                      >
                        <Link
                          href={href}
                          className="govuk-link govuk-link--no-visited-state govuk-link--no-underline govuk-!-font-size-16 ml-2"
                          aria-current={isActive ? 'page' : undefined}
                          style={isActive ? { fontWeight: 'bold' } : undefined}
                        >
                          {minute.template_name}
                        </Link>
                        <p className="govuk-body-s govuk-!-font-size-16 ml-2">
                          {date}
                        </p>
                      </li>
                    )
                  })}
                  {minutes.length === 0 && (
                    <li className="govuk-body-s">No summaries yet</li>
                  )}
                </ul>
              </>
            )}
            {transcription && (
              <>
                <NewMinuteDialog
                  transcriptionId={transcriptionId}
                  onCreated={() =>
                    router.push(`/transcriptions/${transcriptionId}/summary`)
                  }
                />
              </>
            )}
          </li>
          <li id="tour-transcript" className="flex-1">
            <Link
              href={`/transcriptions/${transcriptionId}/transcript`}
              className={`govuk-link govuk-link--no-visited-state govuk-link--no-underline border-l-4 border-[transparent] pl-4 ${transcriptPage ? '!border-(--govuk-link-colour) font-bold' : ''}`}
              aria-current={transcriptPage ? 'page' : undefined}
            >
              Transcript
            </Link>
          </li>
        </ul>
      </nav>
    </div>
  )
}
