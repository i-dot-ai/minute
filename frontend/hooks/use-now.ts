'use client'

import { useEffect, useState } from 'react'

const DEFAULT_INTERVAL_MS = 15 * 1000

/**
 * The current time, re-rendered on an interval so values derived from it stay
 * fresh. Returns null until mounted, so the server and the first client render
 * agree; callers should treat that as "no time has passed yet".
 */
export function useNow({
  enabled = true,
  intervalMs = DEFAULT_INTERVAL_MS,
}: { enabled?: boolean; intervalMs?: number } = {}) {
  const [now, setNow] = useState<number | null>(null)

  useEffect(() => {
    if (!enabled) return
    setNow(Date.now())
    const id = setInterval(() => setNow(Date.now()), intervalMs)
    return () => clearInterval(id)
  }, [enabled, intervalMs])

  return now
}
