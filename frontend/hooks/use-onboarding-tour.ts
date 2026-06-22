'use client'

import { GovukJoyrideTooltip } from '@/components/onboarding/govuk-joyride-tooltip'
import { ORIGIN, useJoyride, type Props, type Step } from 'react-joyride'

export const ONBOARDING_STORAGE_KEY = 'minute-onboarding-tour'
export const RESTART_ONBOARDING_TOUR_EVENT = 'restart-onboarding-tour'

export function requestOnboardingTourRestart() {
  window.dispatchEvent(new Event(RESTART_ONBOARDING_TOUR_EVENT))
}
export const NEW_TRANSCRIPTION_NAV_STEP_INDEX = 4
export const SAVED_TRANSCRIPTIONS_NAV_STEP_INDEX = 6
export const TEMPLATES_NAV_STEP_INDEX = 8
export const SETTINGS_NAV_STEP_INDEX = 12

export const onboardingSteps: Step[] = [
  {
    target: 'body',
    placement: 'center',
    skipScroll: true,
    content: 'Welcome to Minute. This tour will show you around.',
    title: 'Welcome',
  },
  {
    target: '.govuk-button--start',
    content: 'Click here to start a new transcription.',
    placement: 'top',
  },
  {
    target: '.govuk-width-container.govuk-main-wrapper',
    content: 'Your most recent transcriptions will be displayed here.',
    placement: 'top',
  },
  {
    target: '.govuk-service-navigation__wrapper',
    content:
      'You can also navigate across the app using the navigation bar here.',
    placement: 'bottom',
  },
  {
    target: '[data-onboarding="new-transcription-nav"]',
    content:
      'Click "New transcription" to open see how to start a new transcription.',
    placement: 'bottom',
    blockTargetInteraction: false,
    buttons: ['back', 'close'],
  },
  {
    target: '[data-onboarding="new-transcription-page"]',
    content:
      'You can use minute to record a virtual meeting in another tab, record audio directly from your device, or upload a file from your computer. Each step is explained when you click on through.',
    placement: 'top',
  },
  {
    target: '[data-onboarding="saved-transcriptions-nav"]',
    content:
      'Click "Saved transcriptions" to see where your transcriptions are stored.',
    placement: 'bottom',
    blockTargetInteraction: false,
    buttons: ['back', 'close'],
  },
  {
    target: '[data-onboarding="saved-transcriptions-page"]',
    content:
      'All your saved transcriptions will be listed here. From this page you can view, edit, delete and generate new summaries.',
    placement: 'right',
  },
  {
    target: '[data-onboarding="templates-nav"]',
    content: 'Click "Templates" to see how you can customise your minutes.',
    placement: 'bottom',
    blockTargetInteraction: false,
    buttons: ['back', 'close'],
  },
  {
    target: '[data-onboarding="templates-page"]',
    content:
      'Templates are used to customise the structure and style of your summaries. There are two types of templates:',
    placement: 'left',
  },
  {
    target: '[data-onboarding="document-templates"]',
    content:
      'Document templates help to control the structure and style of your summaries.',
    placement: 'top',
  },
  {
    target: '[data-onboarding="form-templates"]',
    content:
      'Form templates are used by setting questions that should be answered in the summary. You can also customise the style that the answers should take.',
    placement: 'top',
  },
  {
    target: '[data-onboarding="settings-nav"]',
    content: 'Click "Settings" to manage your account preferences.',
    placement: 'bottom',
    blockTargetInteraction: false,
    buttons: ['back', 'close'],
  },
  {
    target: '[data-onboarding="settings-page"]',
    content:
      'You can set your data retention period here. After this period the transcriptions, minutes and audio recording will be permentantly deleted.',
    placement: 'right',
  },
]

type UseOnboardingTourOptions = Omit<
  Props,
  'steps' | 'continuous' | 'scrollToFirstStep'
>

export function useOnboardingTour({
  options,
  onEvent,
  run = true,
  ...props
}: UseOnboardingTourOptions = {}) {
  return useJoyride({
    steps: onboardingSteps,
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
