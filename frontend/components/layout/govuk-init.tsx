'use client'

import { useEffect } from 'react'

export function GovukInit() {
  useEffect(() => {
    document.body.classList.add('js-enabled')

    import('govuk-frontend').then(({ createAll, ServiceNavigation }) => {
      createAll(ServiceNavigation)
    })
  }, [])

  return null
}