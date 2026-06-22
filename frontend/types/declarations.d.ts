// Included to fix type issue in audio-player.tsx
// To support older browsers we support the case where webkitAudioContext is used instead of AudioContext
// Typescript doesn't include webkitAudioContext in it's type definition for Window.
// So here we add it.
declare interface Window {
  webkitAudioContext: typeof AudioContext
}

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
