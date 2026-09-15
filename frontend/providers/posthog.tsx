'use client'

import { getUserUsersMeGetOptions } from '@/lib/client/@tanstack/react-query.gen'
import { useQuery } from '@tanstack/react-query'
import { usePathname, useSearchParams } from 'next/navigation'
import posthog from 'posthog-js'
import { PostHogProvider } from 'posthog-js/react'
import React, { Suspense, useEffect, PropsWithChildren } from 'react'

function PageviewTracker() {
  const pathname = usePathname()
  const searchParams = useSearchParams()

  useEffect(() => {
    if (!posthog.__loaded) {
      return
    }
    let url = window.origin + pathname
    const search = searchParams.toString()
    if (search) {
      url = `${url}?${search}`
    }
    posthog.capture('$pageview', { $current_url: url })
  }, [pathname, searchParams])

  return null
}

function PosthogProvider({ children }: PropsWithChildren) {
  const { data: user } = useQuery({ ...getUserUsersMeGetOptions() })

  useEffect(() => {
    const API_KEY = process.env.NEXT_PUBLIC_POSTHOG_API_KEY
    if (!API_KEY) {
      return
    }
    posthog.init(API_KEY, {
      api_host: 'https://eu.i.posthog.com',
      persistence: 'memory',
      autocapture: false,
      disable_session_recording: true,
      capture_pageview: false,
    })

    if (user?.id) {
      posthog.identify(user.id, { email_domain: user.email?.split('@')[1] })
    }
  }, [user?.id])

  return (
    <PostHogProvider client={posthog}>
      <Suspense fallback={null}>
        <PageviewTracker />
      </Suspense>
      {children}
    </PostHogProvider>
  )
}

export default PosthogProvider
