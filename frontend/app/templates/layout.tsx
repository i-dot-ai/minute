import { HistoryBackButton } from '@/components/ui/history-back-button'
import { ReactElement } from 'react'

export default async function TemplatesLayout({
  children,
}: {
  children: ReactElement
}) {
  return (
    <div className="p-6 pt-1">
      <HistoryBackButton />
      {children}
    </div>
  )
}
