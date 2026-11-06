'use client'

import { useEffect } from 'react'

export function DesignKitInit() {
  useEffect(() => {
    const init = async () => {
      const { initAll } = await import('govuk-frontend')
      const { initAllIAIDesignSystem } = await import(
        '@i-dot-ai-npm/component-library-frontend'
      )
      initAll()
      initAllIAIDesignSystem()
    }
    init()
  }, [])

  return null
}
