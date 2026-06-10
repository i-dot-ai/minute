import { RefObject, useEffect } from 'react'

type GovukComponentInstance = { teardown?: () => void }

type GovukComponentClass = {
  new (root: HTMLElement): GovukComponentInstance
  moduleName: string
}

type GovukComponentName = 'FileUpload' | 'Radios' | 'Tabs'

const hasRequiredInputs = (
  root: HTMLElement,
  componentName: GovukComponentName
) => {
  if (componentName === 'Radios') {
    return root.querySelector('input[type="radio"]') !== null
  }
  if (componentName === 'FileUpload') {
    return root.querySelector('input[type="file"]') !== null
  }
  return true
}

export function useGovukModule(
  ref: RefObject<HTMLElement | null>,
  componentName: GovukComponentName,
  enabled = true
) {
  useEffect(() => {
    if (!enabled) return

    const root = ref.current
    if (!root || !hasRequiredInputs(root, componentName)) return

    let cancelled = false
    let instance: GovukComponentInstance | null = null

    import('govuk-frontend').then((govuk) => {
      if (cancelled) return

      const Component = govuk[componentName] as GovukComponentClass
      const initAttr = `data-${Component.moduleName}-init`
      if (root.hasAttribute(initAttr)) return
      if (!hasRequiredInputs(root, componentName)) return

      instance = new Component(root)
    })

    return () => {
      cancelled = true
      instance?.teardown?.()
    }
  }, [componentName, enabled, ref])
}
