import { OnboardingTour } from '@/components/onboarding/onboarding-tour'
import { Footer } from '@/components/layout/footer'
import { Header } from '@/components/layout/header'
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
import ServiceNavigation from '@/components/layout/service-navigation'
import UrlMigrationBanner from '@/components/url-migration-banner'

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
    <html lang="en" className={`${inter.className} govuk-template`}>
      <body className="govuk-template__body govuk-frontend-supported">
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
                <ServiceNavigation />
                <RecordingSessionProvider>
                  <div className="ml-38 min-h-screen">
                    <main id="main-content" tabIndex={-1}>
                      {children}
                    </main>
                    {/* <Footer /> */}
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
