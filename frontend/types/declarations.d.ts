declare module '*.html' {
  const content: string
  export default content
}

declare module 'govuk-frontend' {
  export function initAll(): void
  export function createAll(
    component: { moduleName: string; new (root: HTMLElement): unknown },
    config?: object,
    scope?: HTMLElement | Document
  ): unknown[]

  export class Tabs {
    constructor(root: HTMLElement)
    teardown(): void
    static moduleName: string
  }

  export class FileUpload {
    constructor(root: HTMLElement)
    static moduleName: string
  }

  export class Radios {
    constructor(root: HTMLElement)
    static moduleName: string
  }

  export class ServiceNavigation {
    constructor(root: HTMLElement)
    static moduleName: string
  }
}
