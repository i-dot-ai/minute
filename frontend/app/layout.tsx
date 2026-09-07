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
import { TranscriptionSidePanel } from '@/app/transcriptions/[transcriptionId]/MinuteTab/components/TranscriptionSidePanel'
import { Footer } from '@/components/layout/footer'

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
    <html lang="en" className={`${inter.className} govuk-template sm:h-dvh`}>
      <body className="govuk-template__body govuk-frontend-supported sm:h-full sm:overflow-hidden">
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
                  <div className="sm:flex sm:h-dvh sm:flex-col">
                    <Header />
                    <div className="sm:flex sm:min-h-0 sm:flex-1">
                      <ServiceNavigation />
                      <TranscriptionSidePanel />
                      <main
                        id="main-content"
                        tabIndex={-1}
                        className="sm:relative sm:min-h-0 sm:flex-1 sm:overflow-y-auto sm:[scrollbar-gutter:stable]"
                      >
                        {children}
                      </main>
                      <div className="sm:hidden">
                        <Footer />
                      </div>
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
