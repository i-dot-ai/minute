'use client'

import { useEffect, useState } from 'react'

const OLD_URL_HOSTNAME_FRAGMENT = '.cabinetoffice.'

export function useIsOldUrl(): boolean | null {
  const [isOldUrl, setIsOldUrl] = useState<boolean | null>(null)

  useEffect(() => {
    setIsOldUrl(window.location.hostname.includes(OLD_URL_HOSTNAME_FRAGMENT))
  }, [])

  return isOldUrl
}
