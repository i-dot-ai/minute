'use client'

import {
  NEW_TRANSCRIPTION_NAV_STEP_INDEX,
  ONBOARDING_STORAGE_KEY,
  onboardingSteps,
  RESTART_ONBOARDING_TOUR_EVENT,
  SAVED_TRANSCRIPTIONS_NAV_STEP_INDEX,
  SETTINGS_NAV_STEP_INDEX,
  TEMPLATES_NAV_STEP_INDEX,
  useOnboardingTour,
} from '@/hooks/use-onboarding-tour'
import { ACTIONS, EVENTS, STATUS } from 'react-joyride'
import { usePathname, useRouter } from 'next/navigation'
import { useCallback, useEffect, useState } from 'react'

const NAV_STEP_ADVANCES: Record<string, number> = {
  '/new': NEW_TRANSCRIPTION_NAV_STEP_INDEX,
  '/transcriptions': SAVED_TRANSCRIPTIONS_NAV_STEP_INDEX,
  '/templates': TEMPLATES_NAV_STEP_INDEX,
  '/settings': SETTINGS_NAV_STEP_INDEX,
}

function getInitialRun() {
  if (typeof window === 'undefined') return false
  return localStorage.getItem(ONBOARDING_STORAGE_KEY) !== 'done'
}

function getInitialStepIndex() {
  if (typeof window === 'undefined') return 0
  const stored = localStorage.getItem(ONBOARDING_STORAGE_KEY)
  if (!stored || stored === 'done') return 0
  const index = Number(stored)
  return Number.isFinite(index) ? index : 0
}

export function OnboardingTour() {
  const pathname = usePathname()
  const router = useRouter()
  const [run, setRun] = useState(getInitialRun)
  const [stepIndex, setStepIndex] = useState(getInitialStepIndex)

  const finishTour = useCallback(() => {
    localStorage.setItem(ONBOARDING_STORAGE_KEY, 'done')
    setRun(false)
    router.push('/')
  }, [router])

  const restartTour = useCallback(() => {
    localStorage.removeItem(ONBOARDING_STORAGE_KEY)
    setStepIndex(0)
    setRun(false)
    queueMicrotask(() => setRun(true))
  }, [])

  useEffect(() => {
    window.addEventListener(RESTART_ONBOARDING_TOUR_EVENT, restartTour)
    return () =>
      window.removeEventListener(RESTART_ONBOARDING_TOUR_EVENT, restartTour)
  }, [restartTour])

  useEffect(() => {
    if (!run) return
    if (stepIndex >= onboardingSteps.length) {
      finishTour()
      return
    }
    localStorage.setItem(ONBOARDING_STORAGE_KEY, String(stepIndex))
  }, [finishTour, run, stepIndex])

  useEffect(() => {
    const navStepIndex = NAV_STEP_ADVANCES[pathname]
    if (navStepIndex !== undefined && stepIndex === navStepIndex) {
      setStepIndex(navStepIndex + 1)
    }
  }, [pathname, stepIndex])

  const { Tour } = useOnboardingTour({
    run,
    stepIndex,
    onEvent: (data) => {
      if (
        data.type === EVENTS.TOUR_END ||
        data.status === STATUS.SKIPPED ||
        data.status === STATUS.FINISHED
      ) {
        finishTour()
        return
      }

      if (data.type !== EVENTS.STEP_AFTER) return

      if (data.action === ACTIONS.NEXT || data.action === ACTIONS.CLOSE) {
        const nextIndex = data.index + 1
        if (nextIndex >= onboardingSteps.length) {
          finishTour()
        } else {
          setStepIndex(nextIndex)
        }
        return
      }

      if (data.action === ACTIONS.PREV) {
        setStepIndex(data.index - 1)
      }
    },
  })

  return Tour
}
