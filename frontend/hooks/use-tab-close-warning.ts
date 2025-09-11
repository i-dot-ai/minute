import { useLockNavigationContext } from '@/hooks/use-lock-navigation-context'
import { useEffect } from 'react'

export const useTabCloseWarning = (shouldPreventClose: boolean) => {
  const { setLockNavigation } = useLockNavigationContext()
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      e.preventDefault()
      e.returnValue = true
    }
    if (shouldPreventClose) {
      setLockNavigation(true)
      window.addEventListener('beforeunload', handleBeforeUnload)
    }
    return () => {
      setLockNavigation(false)
      window.removeEventListener('beforeunload', handleBeforeUnload)
    }
  }, [shouldPreventClose, setLockNavigation])
}
