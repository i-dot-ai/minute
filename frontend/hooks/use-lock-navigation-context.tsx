'use client'

import {
  createContext,
  Dispatch,
  SetStateAction,
  useContext,
  useState,
} from 'react'

type LockNavigationContextType = {
  lockNavigation: boolean | string
  setLockNavigation: Dispatch<SetStateAction<boolean | string>>
}

const LockNavigationContext = createContext<LockNavigationContextType>({
  lockNavigation: false,
  setLockNavigation: () => {},
})

export const LockNavigationProvider = ({
  children,
}: {
  children: React.ReactNode
}) => {
  const [lockNavigation, setLockNavigation] = useState<string | boolean>(false)

  return (
    <LockNavigationContext.Provider
      value={{ lockNavigation, setLockNavigation }}
    >
      {children}
    </LockNavigationContext.Provider>
  )
}

export const useLockNavigationContext = () => {
  return useContext(LockNavigationContext)
}
