'use client'

import {
  getPageTour,
  RESTART_ONBOARDING_TOUR_EVENT,
  useOnboardingTour,
} from '@/hooks/use-onboarding-tour'
import { EVENTS, STATUS } from 'react-joyride'
import { usePathname } from 'next/navigation'
import { useCallback, useEffect, useMemo, useState } from 'react'

const UNAUTHORISED_PATH = '/unauthorised'

export function OnboardingTour() {
  const pathname = usePathname()
  const [run, setRun] = useState(false)
  const [targetMissing, setTargetMissing] = useState(false)

  const tour = useMemo(
    () => (pathname === UNAUTHORISED_PATH ? undefined : getPageTour(pathname)),
    [pathname]
  )
  const steps = useMemo(() => tour?.steps ?? [], [tour])
  const tourKey = tour?.key
  const hasTour = steps.length > 0
  const tourActive = run && hasTour

  const finishTour = useCallback(() => {
    setRun(false)
  }, [])

  // Stop the tour when navigating to a different page.
  useEffect(() => {
    setRun(false)
  }, [tourKey])

  const startTour = useCallback(() => {
    if (!hasTour) return
    setRun(false)
    queueMicrotask(() => setRun(true))
  }, [hasTour])

  useEffect(() => {
    window.addEventListener(RESTART_ONBOARDING_TOUR_EVENT, startTour)
    return () =>
      window.removeEventListener(RESTART_ONBOARDING_TOUR_EVENT, startTour)
  }, [startTour])

  // If a tour is running but its target element isn't present, react-joyride
  // renders its grey overlay with no tooltip. Detect that so the user can
  // click the overlay to close the tour.
  useEffect(() => {
    setTargetMissing(false)

    if (!tourActive) return

    const target = steps[0]?.target
    if (typeof target !== 'string') return

    const timeout = setTimeout(() => {
      setTargetMissing(!document.querySelector(target))
    }, 1200)

    return () => clearTimeout(timeout)
  }, [tourActive, steps])

  const { Tour } = useOnboardingTour({
    run: tourActive,
    steps,
    onEvent: (data) => {
      if (
        data.type === EVENTS.TOUR_END ||
        data.status === STATUS.SKIPPED ||
        data.status === STATUS.FINISHED
      ) {
        finishTour()
      }
    },
  })

  return (
    <>
      {Tour}
      {tourActive && targetMissing && (
        <div
          role="button"
          aria-label="Close tour"
          tabIndex={0}
          onClick={finishTour}
          onKeyDown={(event) => {
            if (event.key === 'Enter' || event.key === ' ') finishTour()
          }}
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 10000,
            cursor: 'pointer',
          }}
        />
      )}
    </>
  )
}
