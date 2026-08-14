'use client'

import { GovukJoyrideTooltip } from '@/components/onboarding/govuk-joyride-tooltip'
import { ORIGIN, useJoyride, type Props, type Step } from 'react-joyride'

export const ONBOARDING_STORAGE_KEY = 'minute-onboarding-tour'
export const RESTART_ONBOARDING_TOUR_EVENT = 'restart-onboarding-tour'

export function requestOnboardingTourRestart() {
  window.dispatchEvent(new Event(RESTART_ONBOARDING_TOUR_EVENT))
}

function selectRadioCard(
  mode: 'in-person' | 'virtual-meeting' | 'upload-file'
) {
  document.getElementById(mode)?.click()
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
        content:
          'Each page has a new guide to help you get started. Click the "Tour this page" button in the left-hand navigation to get a tour of that page.',
        title: 'Welcome to Minute',
      },
      {
        target: '.govuk-radios--cards',
        content:
          'Record in the room, capture a virtual call, or upload audio you already have.',
        title: 'Choose how to capture',
        before: async () => {
          selectRadioCard('in-person')
        },
      },
      {
        target: '#tour-select-microphone',
        content:
          'The current input device is shown here. Run a quick check before a real meeting to make sure sound is coming through.',
        title: 'Check your microphone',
      },
      {
        target: '.govuk-button',
        content: 'When you’re ready, start here.',
        title: 'Start recording',
        before: async () => {
          selectRadioCard('in-person')
        },
      },
      {
        target: '#virtual-meeting-card',
        content:
          'Select this option to record virtual meetings such as Zoom, Microsoft Teams, or Google Meet.',
        title: 'Virtual meetings',
        before: async () => {
          selectRadioCard('virtual-meeting')
        },
      },
      {
        target: '#virtual-meeting-before-start',
        content:
          'Read the instructions here carefully before starting your meeting.',
        title: 'Before you start',
      },
      {
        target: '#tour-select-microphone',
        content:
          'Choose your microphone, this will be used to capture your voice.',
        title: 'Microphone',
      },
      {
        target: '#virtual-meeting-audio-not-picking-up',
        content:
          'If you are having audio or screen share issues, check the further instructions here.',
        title: 'Audio or screen share not picking up?',
        before: async () => {
          selectRadioCard('virtual-meeting')
        },
      },
      {
        target: '#upload-file-card',
        content:
          'Select this option to generate a transcript and summary from an audio file on your computer.',
        title: 'Upload a file',
        before: async () => {
          selectRadioCard('upload-file')
        },
      },
      {
        target: '.govuk-file-upload-wrapper',
        content:
          'Drag your audio file here or click to browse your files to upload it.',
        title: 'Choose file to upload',
        before: async () => {
          selectRadioCard('upload-file')
        },
      },
      {
        target: '.govuk-service-navigation',
        placement: 'right',
        content:
          'Your transcriptions, templates are here. You can always restart a tour by clicking the "Tour this page" button in the left-hand navigation.',
        title: 'Everything else lives here',
      },
    ],
  },
  {
    key: 'transcriptions',
    match: (pathname) => pathname === '/transcriptions',
    steps: [
      {
        target: 'table',
        placement: 'center',
        content:
          'All your saved transcriptions and recordings will be listed here.',
        title: 'Transcriptions',
      },
      {
        target: '#tour-data-retention',
        content:
          'All transcriptions and recordings will be deleted after your data retention period. You can change this in the link here.',
        title: 'Data retention',
      },
      {
        target: '#search-transcriptions',
        content: 'Search for transcriptions by meeting title.',
        title: 'Search for transcriptions',
      },
      {
        target: '.govuk-checkboxes',
        content: 'Select one or more transcriptions to bulk delete meetings.',
        title: 'Select transcriptions',
      },
      {
        target: '#tour-filter',
        content:
          'Filter transcriptions by expiring soon, failed or incomplete recordings.',
        title: 'Filter',
      },
      {
        target: '.govuk-table',
        content:
          'If you have recorded or uploaded any meetings, they will be listed here. You can click through to view and edit the full transcriptions or summaries.',
        title: 'Transcriptions',
      },
    ],
  },
  {
    key: 'templates',
    match: (pathname) => pathname === '/templates',
    steps: [
      {
        target: 'table',
        placement: 'center',
        content:
          'All the system templates and your custom templates are listed here.',
        title: 'Templates',
      },
      {
        target: '#search-templates',
        content: 'Search for templates by title.',
        title: 'Search for templates',
      },
      {
        target: '.govuk-button',
        content:
          'Create a new template by clicking the button here. You can either start with a blank template or use an example template as a starting point.',
        title: 'Create a new template',
      },
      {
        target: '.govuk-checkboxes',
        content:
          'Select one or more templates to bulk delete them. (Only custom templates can be deleted)',
        title: 'Select templates',
      },
      {
        target: '#tour-filter',
        content: 'Filter templates by type (system, Q & A or Summary).',
        title: 'Filter',
      },
      {
        target: '.govuk-table',
        content:
          'Templates are listed here. You can click through to set defaults, or view and edit the custom templates.',
        title: 'Templates',
      },
    ],
  },
  {
    key: 'transcription-summary',
    match: (pathname) =>
      pathname.startsWith('/transcriptions/') && pathname.includes('/summary'),
    steps: [
      {
        target: '#tour-summary',
        placement: 'center',
        content: 'The summary is displayed here.',
        title: 'Summary',
      },
      {
        target: '#tour-show-references',
        content:
          'Show references to easily view where in the transcript the summary is referencing. Or hide them for easier reading.',
        title: 'Show references',
      },
      {
        target: '#tour-export-summary',
        content:
          'Export the summary to a Word document or copy the text to your clipboard.',
        title: 'Export',
      },
      {
        target: '#tour-edit-summary',
        content:
          'You can edit the text manually or with AI, update the speaker names, or go through the version history.',
        title: 'Edit',
      },
      {
        target: '#tour-delete-summary',
        content:
          'Delete the summary here. This will only delete this summary, all other summaries, transcriptions and recordings will remain.',
        title: 'Delete summary',
      },
      {
        target: '#tour-summaries',
        content:
          'Click "new summary" to generate a new summary. All generated summaries will be listed here to easily switch between them.',
        title: 'Summaries',
      },
    ],
  },
  {
    key: 'transcription-transcript',
    match: (pathname) =>
      pathname.startsWith('/transcriptions/') && !pathname.includes('/summary'),
    steps: [
      {
        target: '.secondary-nav',
        content:
          'This is the full transcript. You can edit the text, rename speakers, and switch back to your summaries here.',
        title: 'Transcript',
      },
    ],
  },
  {
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
      showProgress: true,
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
