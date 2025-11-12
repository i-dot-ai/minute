import { ReactElement } from 'react'

export default function TranscriptionsLayout({
  children,
}: {
  children: ReactElement
}) {
  return <div className="p-6">{children}</div>
}
