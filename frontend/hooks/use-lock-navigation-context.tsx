'use client'

import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import {
  createContext,
  Dispatch,
  SetStateAction,
  useCallback,
  useContext,
  useRef,
  useState,
} from 'react'

type LockNavigationContextType = {
  lockNavigation: boolean
  setLockNavigation: Dispatch<SetStateAction<boolean>>
  requestNavigation: (proceed: () => void) => boolean
}

const LockNavigationContext = createContext<LockNavigationContextType>({
  lockNavigation: false,
  setLockNavigation: () => {},
  requestNavigation: (proceed) => {
    proceed()
    return true
  },
})

export const LockNavigationProvider = ({
  children,
}: {
  children: React.ReactNode
}) => {
  const [lockNavigation, setLockNavigation] = useState(false)
  const [open, setOpen] = useState(false)
  const pendingRef = useRef<(() => void) | null>(null)

  const requestNavigation = useCallback(
    (proceed: () => void) => {
      if (!lockNavigation) {
        proceed()
        return true
      }
      pendingRef.current = proceed
      setOpen(true)
      return false
    },
    [lockNavigation]
  )

  const handleConfirm = useCallback(() => {
    const proceed = pendingRef.current
    pendingRef.current = null
    setOpen(false)
    setLockNavigation(false)
    proceed?.()
  }, [])

  const handleCancel = useCallback(() => {
    pendingRef.current = null
    setOpen(false)
  }, [])

  return (
    <LockNavigationContext.Provider
      value={{ lockNavigation, setLockNavigation, requestNavigation }}
    >
      {children}
      <AlertDialog
        open={open}
        onOpenChange={(next) => {
          if (!next) handleCancel()
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="govuk-heading-l">
              Are you sure you want to leave the page?
            </AlertDialogTitle>
            <AlertDialogDescription className="govuk-body">
              The current recording will stop if you leave this page.
              <br />
              <br />
              Your recording will be discarded if you do not upload it, or save
              a local copy.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <div className="govuk-button-group">
              <AlertDialogCancel onClick={handleCancel}>
                Cancel
              </AlertDialogCancel>
              <button
                type="button"
                className="govuk-button"
                onClick={handleConfirm}
              >
                Continue
              </button>
            </div>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </LockNavigationContext.Provider>
  )
}

export const useLockNavigationContext = () => {
  return useContext(LockNavigationContext)
}
