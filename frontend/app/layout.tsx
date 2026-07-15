import { OnboardingTour } from '@/components/onboarding/onboarding-tour'
import { GovukInit } from '@/components/layout/govuk-init'
import { LockNavigationProvider } from '@/hooks/use-lock-navigation-context'
import { TanstackQueryProvider } from '@/providers/TanstackQueryProvider'
import PosthogProvider from '@/providers/posthog'
import { RecordingDbProvider } from '@/providers/transcription-db-provider'
import { RecordingSessionProvider } from '@/providers/recording-session-provider'
import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import { Toaster } from 'sonner'
import Link from 'next/link'
import './globals.css'
import { Header } from '@/components/layout/header'
import ServiceNavigation from '@/components/layout/service-navigation'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Minute',
  description: 'Minutes and transcriptions',
  icons: {
    icon: '/images/favicon.ico',
  },
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" className={`${inter.className} govuk-template h-full`}>
      <body className="govuk-template__body govuk-frontend-supported h-full overflow-hidden">
        <GovukInit />
        <TanstackQueryProvider>
          <PosthogProvider>
            <LockNavigationProvider>
              <RecordingDbProvider>
                <Link
                  href="#main-content"
                  className="govuk-skip-link"
                  data-module="govuk-skip-link"
                >
                  Skip to main content
                </Link>
                <OnboardingTour />
                <RecordingSessionProvider>
                  <div className="flex h-dvh flex-col">
                    <Header />
                    <div className="flex min-h-0 flex-1">
                      <ServiceNavigation />
                      <main
                        id="main-content"
                        tabIndex={-1}
                        className="min-h-0 flex-1 overflow-y-auto"
                      >
                        {children}
                      </main>
                    </div>
                  </div>
                </RecordingSessionProvider>
                <Toaster />
              </RecordingDbProvider>
            </LockNavigationProvider>
          </PosthogProvider>
        </TanstackQueryProvider>
      </body>
    </html>
  )
}
