'use client'

import { NewMinuteDialog } from '@/app/transcriptions/[transcriptionId]/MinuteTab/NewMinuteDialog'
import { DeleteTranscriptionButton } from '@/components/recent-meetings/delete-transcription-button'
import { getTranscriptionTranscriptionsTranscriptionIdGetOptions, listMinutesForTranscriptionTranscriptionTranscriptionIdMinutesGetOptions } from '@/lib/client/@tanstack/react-query.gen'
import { useQuery } from '@tanstack/react-query'
import Link from 'next/link'
import { useParams, usePathname, useRouter } from 'next/navigation'

export function TranscriptionSidePanel() {
  const { transcriptionId } = useParams<{ transcriptionId?: string }>()
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
    <div className="govuk-!-padding-top-4 govuk-!-padding-right-6 govuk-!-padding-left-6 overflow-y-auto bg-[#f3f3f3]">
      {transcription && (
        <div className="border-b border-(--govuk-border-colour) govuk-!-margin-bottom-4">
          <div className="govuk-button-group justify-center flex-col govuk-!-margin-bottom-0">
            <DeleteTranscriptionButton transcription={transcription} />
          </div>
        </div>
      )}
      <nav
        aria-label="Summaries and transcript"
        className="secondary-nav"
      >
        <ul className="govuk-list govuk-list--spaced">
          <li
            className={`w-50 border-l-4 border-[transparent] pl-4 ${!transcriptPage ? '!border-(--govuk-link-colour)' : ''}`}
          >
            {transcriptPage || minutes.length <= 1 ? (
              <Link
                href={`/transcriptions/${transcriptionId}/summary`}
                className="govuk-link govuk-link--no-visited-state govuk-link--no-underline"
              >
                {minutes.length > 1 ? 'Summaries' : 'Summary'}
              </Link>
            ) : (
              <>
                <h2 className="govuk-caption-s font-normal text-[#484949]">
                  Summaries
                </h2>
                <ul className="govuk-list !pl-[20px]">
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
                          className="govuk-link govuk-link--no-visited-state govuk-link--no-underline ml-2"
                          aria-current={isActive ? 'page' : undefined}
                          style={isActive ? { fontWeight: 'bold' } : undefined}
                        >
                          {minute.template_name}
                        </Link>
                        <p className="govuk-body-s ml-2">{date}</p>
                      </li>
                    )
                  })}
                  {minutes.length === 0 && (
                    <li className="govuk-body-s">No summaries yet</li>
                  )}
                </ul>
              </>
            )}
          </li>
          <li>
            <Link
              href={`/transcriptions/${transcriptionId}/transcript`}
              className={`govuk-link govuk-link--no-visited-state govuk-link--no-underline border-l-4 border-[transparent] pl-2 ${transcriptPage ? '!border-(--govuk-link-colour) font-bold' : ''}`}
              aria-current={transcriptPage ? 'page' : undefined}
            >
              Transcript
            </Link>
          </li>
        </ul>
      </nav>
      <div className="govuk-button-group justify-center flex-col govuk-!-margin-bottom-0">
        <div className="border-t border-(--govuk-border-colour) govuk-!-padding-top-4">
          <NewMinuteDialog
            transcriptionId={transcriptionId}
            onCreated={() =>
              router.push(`/transcriptions/${transcriptionId}/summary`)
            }
          />
        </div>
      </div>
    </div>
  )
}
