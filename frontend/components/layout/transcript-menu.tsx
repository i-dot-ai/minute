'use client'

import {
  getTranscriptionTranscriptionsTranscriptionIdGetOptions,
  listMinutesForTranscriptionTranscriptionTranscriptionIdMinutesGetOptions,
} from '@/lib/client/@tanstack/react-query.gen'
import { useQuery } from '@tanstack/react-query'
import Link from 'next/link'
import { useState } from 'react'
import { useParams, usePathname } from 'next/navigation'
import { ChevronDown, ChevronUp } from 'lucide-react'

export function TranscriptMenu() {
  const { transcriptionId } = useParams<{ transcriptionId?: string }>()
  const [areSummariesCollapsed, setAreSummariesCollapsed] = useState(false)
  const pathname = usePathname()

  if (!transcriptionId) return null

  const { data: minutes = [] } = useQuery({
    ...listMinutesForTranscriptionTranscriptionTranscriptionIdMinutesGetOptions(
      {
        path: { transcription_id: transcriptionId },
      }
    ),
    enabled: !!transcriptionId,
  })
  const { data: transcription, isLoading } = useQuery({
    ...getTranscriptionTranscriptionsTranscriptionIdGetOptions({
      path: { transcription_id: transcriptionId },
    }),
  })
  const transcriptPage = !pathname.includes('/summary')

  return (
    <div className="w-[200px]">
      <h2 className="govuk-!-margin-left-4 govuk-!-padding-top-2 govuk-!-padding-bottom-2 text-[0.875rem]">
        {transcription?.title}
      </h2>
      <ul className="govuk-list govuk-!-margin-left-4">
        <li
          id="tour-transcript"
          className={`govuk-!-padding-top-1 govuk-!-padding-bottom-1 flex-1 border-l-4 border-[transparent] pl-4 ${transcriptPage ? '!border-(--govuk-link-colour) bg-[#d2e2f1] font-bold' : ''}`}
        >
          <Link
            href={`/transcriptions/${transcriptionId}/transcript`}
            className={`govuk-link govuk-link--no-visited-state govuk-link--no-underline text-[0.875rem] ${transcriptPage ? '!text-(--govuk-text-colour)' : ''}`}
            aria-current={transcriptPage ? 'page' : undefined}
          >
            Transcript
          </Link>
        </li>
        <li id="tour-summaries" className="govuk-!-margin-bottom-0 flex-1">
          <button
            onClick={() => setAreSummariesCollapsed((prev) => !prev)}
            className="govuk-!-padding-left-4 govuk-!-padding-right-2 govuk-!-padding-top-1 govuk-!-padding-bottom-1 flex w-full cursor-pointer items-center justify-between hover:bg-[#d2e2f1]"
          >
            <h2 className="govuk-caption-s text-[0.875rem] font-normal text-(--govuk-text-colour)">
              Summaries
            </h2>
            {areSummariesCollapsed ? <ChevronDown /> : <ChevronUp />}
            <span className="govuk-visually-hidden">
              {areSummariesCollapsed ? 'Expand' : 'Collapse'} summary details
            </span>
          </button>
          {!areSummariesCollapsed && (
            <ul className="govuk-list govuk-!-margin-bottom-0 govuk-!-margin-left-4">
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
                    className={`govuk-!-padding-left-3 govuk-!-padding-right-2 govuk-!-margin-0 flex-1 border-l-4 border-[#8eb8dc] py-1 ${isActive ? '!border-(--govuk-link-colour) bg-[#d2e2f1] font-bold' : ''}`}
                  >
                    <Link
                      href={href}
                      className={`govuk-link govuk-link--no-visited-state govuk-link--no-underline text-[0.875rem] ${isActive ? '!text-(--govuk-text-colour)' : ''}`}
                      aria-current={isActive ? 'page' : undefined}
                      style={isActive ? { fontWeight: 'bold' } : undefined}
                    >
                      {minute.template_name}
                    </Link>
                    <p className="govuk-body-s govuk-!-margin-bottom-1 !text-[0.875rem]">
                      {date}
                    </p>
                  </li>
                )
              })}
              {minutes.length === 0 && (
                <li className="govuk-body-s">No summaries yet</li>
              )}
            </ul>
          )}
        </li>
      </ul>
    </div>
  )
}
