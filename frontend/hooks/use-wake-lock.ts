import { useCallback, useEffect, useRef } from 'react'

export const useWakeLock = () => {
  const wakeLockRef = useRef<WakeLockSentinel | null>(null)

  const requestWakeLock = useCallback(async () => {
    try {
      if ('wakeLock' in navigator) {
        // Only request wake lock if the page is visible
        const lock = await navigator.wakeLock.request('screen')
        wakeLockRef.current = lock
        lock.addEventListener('release', () => {
          wakeLockRef.current = null
        })
      }
    } catch (e) {
      console.warn('Wake lock request failed, continuing without it:', e)
    }
  }, [])

  useEffect(() => {
    const handleVisibilityChange = async () => {
      if (document.visibilityState === 'visible' && !wakeLockRef.current) {
        await requestWakeLock()
      }
    }
    document.addEventListener('visibilitychange', handleVisibilityChange)
    return () => {
      document.addEventListener('visibilitychange', handleVisibilityChange)
    }
  }, [requestWakeLock])

  const releaseWakeLock = useCallback(async () => {
    if (wakeLockRef.current) {
      await wakeLockRef.current.release()
    }
  }, [])

  // release WakeLock on unmount
  useEffect(() => {
    return () => {
      releaseWakeLock()
    }
  }, [releaseWakeLock])

  return { requestWakeLock, releaseWakeLock }
}
