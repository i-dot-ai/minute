import { OnboardingTour } from '@/components/onboarding/onboarding-tour'
import { Footer } from '@/components/layout/footer'
import { Header } from '@/components/layout/header'
import { GovukInit } from '@/components/layout/govuk-init'
import { LockNavigationProvider } from '@/hooks/use-lock-navigation-context'
import { TanstackQueryProvider } from '@/providers/TanstackQueryProvider'
import PosthogProvider from '@/providers/posthog'
import { RecordingDbProvider } from '@/providers/transcription-db-provider'
import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import { Toaster } from 'sonner'
import './globals.css'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Minute',
  description: 'Minutes and transcriptions',
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
                <Header />
                <OnboardingTour />
                <main id="main-content">{children}</main>
                <Footer />
                <Toaster />
              </RecordingDbProvider>
            </LockNavigationProvider>
          </PosthogProvider>
        </TanstackQueryProvider>
      </body>
    </html>
  )
}
