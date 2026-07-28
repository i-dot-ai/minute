'use client'

import { GovukJoyrideTooltip } from '@/components/onboarding/govuk-joyride-tooltip'
import { ORIGIN, useJoyride, type Props, type Step } from 'react-joyride'

export const ONBOARDING_STORAGE_KEY = 'minute-onboarding-tour'
export const RESTART_ONBOARDING_TOUR_EVENT = 'restart-onboarding-tour'

export function requestOnboardingTourRestart() {
  window.dispatchEvent(new Event(RESTART_ONBOARDING_TOUR_EVENT))
}

export type PageTour = {
  key: string
  match: (pathname: string) => boolean
  steps: Step[]
}

export const pageTours: PageTour[] = [
  {
    key: 'home',
    match: (pathname) => pathname === '/',
    steps: [
      {
        target: 'body',
        placement: 'center',
        skipScroll: true,
        buttons: ['close'],
        content:
          'We have recently updated the styling of the app. Everything is in the same place, just with a new look.',
        title: 'Welcome to Minute',
      },
    ],
  },
  {
    key: 'transcriptions',
    match: (pathname) => pathname === '/transcriptions',
    steps: [
      {
        target: '[data-onboarding="saved-transcriptions-page"]',
        content:
          'All your saved transcriptions will be listed here. From this page you can view, edit, delete and generate new summaries.',
        placement: 'right',
      },
    ],
  },
  {
    key: 'templates',
    match: (pathname) => pathname === '/templates',
    steps: [
      {
        target: '[data-onboarding="templates-page"]',
        content:
          'Templates are used to customise the structure and style of your summaries. There are document templates and form templates.',
        placement: 'left',
      },
    ],
  },
  {
    // Shown once you are inside a transcription, on either the summary or the
    // transcript view (both share the same secondary navigation panel).
    key: 'transcription-detail',
    match: (pathname) =>
      /^\/transcriptions\/[^/]+\/(summary|transcript)/.test(pathname),
    steps: [
      {
        target: '[data-onboarding="transcription-detail"]',
        content:
          'Switch between the transcript and any generated summaries here. You can also create a new summary from a different template.',
        placement: 'right',
      },
    ],
  },
  {
    // Template detail / edit page.
    key: 'template-detail',
    match: (pathname) => /^\/templates\/[^/]+$/.test(pathname),
    steps: [
      {
        target: '[data-onboarding="template-detail"]',
        content:
          'View and edit this template here. Use the buttons above to edit, set it as your default, or delete it.',
        placement: 'bottom',
      },
    ],
  },
]

export function getPageTour(pathname: string): PageTour | undefined {
  return pageTours.find((tour) => tour.match(pathname))
}

type UseOnboardingTourOptions = Omit<
  Props,
  'continuous' | 'scrollToFirstStep' | 'steps'
> & {
  steps?: Props['steps']
}

export function useOnboardingTour({
  options,
  onEvent,
  run = true,
  steps = [],
  ...props
}: UseOnboardingTourOptions = {}) {
  return useJoyride({
    steps,
    run,
    continuous: true,
    scrollToFirstStep: true,
    tooltipComponent: GovukJoyrideTooltip,
    options: {
      skipBeacon: true,
      closeButtonAction: 'skip',
      ...options,
    },
    locale: {
      last: 'Finish',
    },
    onEvent: (data, controls) => {
      if (data.origin === ORIGIN.OVERLAY) {
        controls.skip()
        return
      }
      onEvent?.(data, controls)
    },
    ...props,
  })
}
