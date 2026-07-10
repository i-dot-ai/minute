'use client'

import { NewMinuteDialog } from '@/app/transcriptions/[transcriptionId]/MinuteTab/NewMinuteDialog'
import { MinuteListItem } from '@/lib/client'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'

export function TranscriptionSidePanel({
  transcriptionId,
  minutes,
  transcriptPage = false,
}: {
  transcriptionId: string
  minutes: MinuteListItem[]
  transcriptPage?: boolean
}) {
  const pathname = usePathname()
  const router = useRouter()

  return (
    <>
      <NewMinuteDialog
        transcriptionId={transcriptionId}
        onCreated={() => router.push(`/transcriptions/${transcriptionId}`)}
      />
      <nav aria-label="Summaries and transcript">
        <ul className="govuk-list govuk-list--spaced">
          <li className={`border-l-4 border-[transparent] pl-4 ${!transcriptPage ? '!border-(--govuk-brand-colour)' : ''}`}>
            {
              transcriptPage || minutes.length <= 1 ? (
                <Link href={`/transcriptions/${transcriptionId}/summary`} className="govuk-link govuk-link--no-visited-state govuk-link--no-underline">{minutes.length > 1 ? 'Summaries' : 'Summary'}</Link>
              ) : (
                <>
                  <h2 className="govuk-caption-s font-normal text-[#484949]">Summaries</h2>
                  <ul className="govuk-list !pl-[20px]">
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
                        <li key={minute.id} className="before:content-['—'] before:text-[#484949] before:ml-[-20px] ">
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
              )
            }
          </li>
          <li>
            <Link
              href={`/transcriptions/${transcriptionId}/transcript`}
              className={`govuk-link govuk-link--no-visited-state govuk-link--no-underline border-l-4 border-[transparent] pl-2 ${transcriptPage ? 'font-bold !border-(--govuk-brand-colour)' : ''}`}
              aria-current={transcriptPage ? 'page' : undefined}
            >
              Transcript
            </Link>
          </li>
        </ul>
      </nav>
    </>
  )
}

// 'use client'
// import { MinuteTab } from '@/app/transcriptions/[transcriptionId]/MinuteTab/MinuteTab'
// import { NewMinuteDialog } from '@/app/transcriptions/[transcriptionId]/MinuteTab/NewMinuteDialog'
// import { TranscriptionTab } from '@/app/transcriptions/[transcriptionId]/TranscriptionTab/TranscriptionTab'
// import { DownloadButton } from '@/components/download-button'
// import { DeleteTranscriptionButton } from '@/components/recent-meetings/delete-transcription-button'
// import { RenameTranscriptionButton } from '@/components/recent-meetings/rename-transcription-button'
// import { getTranscriptionDisplayTitle } from '@/components/recent-meetings/rename-transcription-dialog'
// import {
//   getRecordingsForTranscriptionTranscriptionsTranscriptionIdRecordingsGetOptions,
//   getTranscriptionTranscriptionsTranscriptionIdGetOptions,
//   listMinutesForTranscriptionTranscriptionTranscriptionIdMinutesGetOptions,
// } from '@/lib/client/@tanstack/react-query.gen'
// import { useQuery } from '@tanstack/react-query'
// import { Loader2 } from 'lucide-react'
// import { AudioWav } from '@/components/icons/AudioWav'
// import Link from 'next/link'
// import { useSearchParams } from 'next/navigation'

// export default function TranscriptionPage({
//   params: { transcriptionId },
// }: {
//   params: { transcriptionId: string }
// }) {
//   const searchParams = useSearchParams()
//   const isTranscriptActive = searchParams.get('active-page') === 'transcript'
//   const minuteId = searchParams.get('minute-id')
//   const { data: transcription, isLoading } = useQuery({
//     ...getTranscriptionTranscriptionsTranscriptionIdGetOptions({
//       path: { transcription_id: transcriptionId },
//     }),
//     refetchInterval: (query) =>
//       query.state.data?.status &&
//         ['awaiting_start', 'in_progress'].includes(query.state.data.status)
//         ? 2000
//         : false,
//   })

//   const minutesEnabled =
//     !!transcription?.status &&
//     !['awaiting_start', 'in_progress', 'failed'].includes(transcription.status)

//   const { data: minutes = [] } = useQuery({
//     ...listMinutesForTranscriptionTranscriptionTranscriptionIdMinutesGetOptions(
//       {
//         path: { transcription_id: transcriptionId },
//       }
//     ),
//     enabled: minutesEnabled,
//   })

//   if (isLoading) {
//     return (
//       <div className="flex items-center gap-2">
//         <Loader2 className="animate-spin" />
//         <p className="govuk-body govuk-!-margin-bottom-0">Loading...</p>
//       </div>
//     )
//   }

//   if (!transcription) {
//     return (
//       <>
//         <p className="govuk-body">404 - Transcription not found</p>
//         <p className="govuk-body">
//           The transcription you are looking for does not exist.
//         </p>
//       </>
//     )
//   }

//   const date = new Date(transcription.created_datetime).toLocaleString(
//     'en-GB',
//     {
//       year: 'numeric',
//       month: 'long',
//       day: 'numeric',
//       hour: '2-digit',
//       minute: '2-digit',
//     }
//   )

//   if (
//     transcription.status &&
//     ['awaiting_start', 'in_progress'].includes(transcription.status)
//   ) {
//     return (
//       <div className="govuk-grid-row govuk-!-margin-bottom-2">
//         <div className="govuk-grid-column-three-quarters">
//           <h1 className="govuk-heading-l govuk-!-margin-bottom-2">
//             Generating transcript
//           </h1>
//           <p className="govuk-body">{date}</p>
//           <p className="govuk-body">
//             The transcription is being processed. Return later to view the
//             transcript.
//           </p>
//           <div className="flex w-full justify-center">
//             <AudioWav />
//           </div>
//           <h2 className="govuk-heading-m">Audio</h2>
//           <AudioPlayer transcriptionId={transcription.id} />
//         </div>
//         <div className="govuk-grid-column-one-quarter">
//           <div className="govuk-button-group">
//             <DeleteTranscriptionButton transcription={transcription} />
//           </div>
//         </div>
//       </div>
//     )
//   }

//   if (transcription.status == 'failed') {
//     return (
//       <>
//         <div className="govuk-grid-row govuk-!-margin-bottom-2">
//           <div className="govuk-grid-column-three-quarters">
//             <h1 className="govuk-heading-xl govuk-!-margin-bottom-2">
//               {getTranscriptionDisplayTitle(
//                 transcription.title,
//                 transcription.status
//               )}
//             </h1>
//             <p className="govuk-body">{date}</p>
//             <p className="govuk-body">
//               The transcription failed to process. Please try again.
//             </p>
//             <p className="govuk-inset-text">
//               You can either{' '}
//               <Link href="/new" className="govuk-link">
//                 start a new transcription
//               </Link>{' '}
//               or download the audio file below and{' '}
//               <Link href="/new/upload" className="govuk-link">
//                 upload it
//               </Link>
//               .
//             </p>
//           </div>
//           <div className="govuk-grid-column-one-quarter">
//             <div className="govuk-button-group transcription-page__actions float-right">
//               <RenameTranscriptionButton transcription={transcription} />
//               <DeleteTranscriptionButton transcription={transcription} />
//             </div>
//           </div>
//         </div>
//         <div className="govuk-grid-row govuk-!-margin-bottom-2">
//           <div className="govuk-grid-column-two-thirds">
//             <h2 className="govuk-heading-m">Audio:</h2>
//             <AudioPlayer transcriptionId={transcription.id} />
//           </div>
//         </div>
//       </>
//     )
//   }

//   const selectedMinuteIndex =
//     !isTranscriptActive && minuteId
//       ? Math.max(
//         0,
//         minutes.findIndex((m) => m.id === minuteId)
//       )
//       : 0

//   return (
//     <div className="govuk-main-wrapper govuk-width-container">
//       <div className="govuk-grid-row">
//         <div className="govuk-grid-column-one-quarter">
//           <h1 className="govuk-heading-s govuk-!-margin-bottom-1">
//             {getTranscriptionDisplayTitle(
//               transcription.title,
//               transcription.status!
//             )}
//           </h1>
//           <p className="govuk-caption-s">
//             {new Date(transcription.created_datetime!).toLocaleString('en-GB', {
//               year: 'numeric',
//               month: 'short',
//               day: 'numeric',
//               hour: '2-digit',
//               minute: '2-digit',
//             })}
//           </p>
//           <div className="govuk-!-margin-top-2 flex items-center gap-4">
//             <RenameTranscriptionButton
//               transcription={{
//                 id: transcription.id!,
//                 title: transcription.title,
//                 status: transcription.status!,
//               }}
//               className="govuk-link govuk-link--no-visited-state flex items-center gap-2 text-(--govuk-link-colour)"
//             />
//             <DeleteTranscriptionButton
//               transcription={{
//                 id: transcription.id!,
//                 title: transcription.title!,
//                 status: transcription.status!,
//                 created_datetime: transcription.created_datetime!,
//               }}
//             />
//           </div>
//           <NewMinuteDialog
//             transcriptionId={transcription.id!}
//             agenda={minutes[selectedMinuteIndex]?.agenda ?? undefined}
//           />
//           <nav className="govuk-!-margin-top-4 border-t border-(--govuk-border-colour) pt-4">
//             <ul className="govuk-list govuk-list--spaced">
//               <li
//                 className={
//                   isTranscriptActive ? '' : 'side-panel__nav-link--active'
//                 }
//               >
//                 {isTranscriptActive || minutes.length <= 1 ? (
//                   <Link
//                     className="govuk-link govuk-link--no-underline govuk-link--no-visited-state"
//                     href="?active-page=summary"
//                   >
//                     Summary
//                   </Link>
//                 ) : (
//                   <>
//                     <h2 className="govuk-caption-s font-normal text-[#484949]">
//                       Summary
//                     </h2>
//                     <ul className="govuk-list govuk-list--spaced side-panel__nav-link-subnav">
//                       {minutes.map((minute, index) => {
//                         const updatedDate = new Date(
//                           minute.updated_datetime
//                         ).toLocaleDateString('en-GB', {
//                           day: 'numeric',
//                           month: 'short',
//                           year: '2-digit',
//                           hour: 'numeric',
//                           minute: 'numeric',
//                         })
//                         const isActive = minuteId
//                           ? minuteId === minute.id
//                           : index === 0
//                         return (
//                           <li
//                             key={minute.id}
//                             className={`side-panel__nav-link-subnav-item ${isActive ? 'font-bold' : ''}`}
//                           >
//                             <Link
//                               href={`?active-page=summary&minute-id=${minute.id}`}
//                               className="govuk-link govuk-link--no-underline govuk-link--no-visited-state"
//                             >
//                               {minute.template_name}
//                             </Link>{' '}
//                             <p className="govuk-!-font-size-16">
//                               {updatedDate}
//                             </p>
//                           </li>
//                         )
//                       })}
//                     </ul>
//                   </>
//                 )}
//               </li>
//               <li>
//                 <Link
//                   className={`govuk-link govuk-link--no-underline ${isTranscriptActive ? 'side-panel__nav-link--active' : ''}`}
//                   href="?active-page=transcript"
//                 >
//                   Transcript
//                 </Link>
//               </li>
//             </ul>
//           </nav>
//         </div>
//         {isTranscriptActive ? (
//           <TranscriptionTab transcription={transcription} />
//         ) : (
//           <MinuteTab
//             transcription={transcription}
//             minutes={minutes}
//             selectedMinuteIndex={selectedMinuteIndex}
//           />
//         )}
//       </div>
//     </div>
//   )
// }

// const AudioPlayer = ({ transcriptionId }: { transcriptionId: string }) => {
//   const { data: recordings } = useQuery({
//     ...getRecordingsForTranscriptionTranscriptionsTranscriptionIdRecordingsGetOptions(
//       { path: { transcription_id: transcriptionId } }
//     ),
//   })
//   if (!recordings || recordings.length == 0) {
//     return null
//   }
//   return (
//     <div>
//       <audio controls src={recordings[0].url} className="w-full" />
//       <div className="govuk-button-group govuk-!-margin-top-2">
//         <DownloadButton recordings={recordings} />
//       </div>
//     </div>
//   )
// }
