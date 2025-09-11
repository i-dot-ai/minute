'use client'

import { getUserUsersMeGetOptions } from '@/lib/client/@tanstack/react-query.gen'
import { useQuery } from '@tanstack/react-query'
import posthog from 'posthog-js'
import { PostHogProvider } from 'posthog-js/react'
import React from 'react'

function PosthogProvider({ children }: React.PropsWithChildren) {
  const { data: user } = useQuery({ ...getUserUsersMeGetOptions() })

  React.useEffect(() => {
    const API_KEY = process.env.NEXT_PUBLIC_POSTHOG_API_KEY
    if (!API_KEY) {
      return
    }
    posthog.init(API_KEY, {
      api_host: 'https://eu.i.posthog.com',
    })

    if (user?.email) {
      posthog.identify(user.email, { email: user.email })
    }
  }, [user?.email])

  return <PostHogProvider client={posthog}>{children}</PostHogProvider>
}

export default PosthogProvider
