'use client'

import { Button } from '@/components/ui/button'
import { ChevronLeft } from 'lucide-react'
import { useRouter } from 'next/navigation'

export const HistoryBackButton = () => {
  const router = useRouter()
  return (
    <Button
      variant="link"
      className="mb-4 self-start px-0! underline hover:decoration-2"
      onClick={() => {
        router.back()
      }}
    >
      <span className="flex items-center">
        <ChevronLeft />
        Back
      </span>
    </Button>
  )
}
