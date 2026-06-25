'use client'

import { useEffect, useState } from 'react'

const OLD_URL_HOSTNAME_FRAGMENT = '.cabinetoffice.'

export function useIsOldUrl(): boolean {
  const [isOldUrl, setIsOldUrl] = useState(false)

  useEffect(() => {
    setIsOldUrl(window.location.hostname.includes(OLD_URL_HOSTNAME_FRAGMENT))
  }, [])

  return isOldUrl
}
