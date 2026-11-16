'use client'

import { readSearchMatch } from '@/lib/search-match'
import { usePathname, useSearchParams } from 'next/navigation'
import { useEffect, useState } from 'react'

export function useSearchMatch() {
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const [match, setMatch] = useState<ReturnType<typeof readSearchMatch>>(null)
  useEffect(() => {
    const update = () => setMatch(readSearchMatch())
    update()
    window.addEventListener('hashchange', update)
    return () => window.removeEventListener('hashchange', update)
  }, [pathname, searchParams])
  return match
}
