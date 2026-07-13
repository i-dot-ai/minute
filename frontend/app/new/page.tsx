'use client'

import { MicRecorderForm } from '@/components/audio/mic-recorder'
import { TabRecorderForm } from '@/components/audio/tab-recorder/tab-recorder'
import { useRecordingSession } from '@/providers/recording-session-provider'
import { useRouter } from 'next/navigation'
import { useEffect } from 'react'

export default function RecordPage() {
  const router = useRouter()
  const { mode, screenStream, devices, selectedDeviceId, reset } =
    useRecordingSession()

  const missingSession = !mode || (mode === 'virtual-meeting' && !screenStream)

  useEffect(() => {
    if (missingSession) router.replace('/')
  }, [missingSession, router])

  if (missingSession) return null

  const handleStarted = (id: string) => router.push(`/new/status/${id}`)
  const handleDiscard = () => {
    reset()
    router.push('/')
  }

  return (
    <div className="govuk-width-container govuk-main-wrapper">
      <div className="govuk-grid-row">
        <div className="govuk-grid-column-full">
          {/* <h1 className="govuk-heading-l">New meeting</h1> */}
          <p className="govuk-hint">
            Please ensure that all participants are aware that they have been
            recorded. Suitable up to <strong>OFFICIAL SENSITIVE</strong>.
          </p>
          {mode === 'in-person' ? (
            <MicRecorderForm
              initialDevices={devices}
              initialDeviceId={selectedDeviceId}
              onDiscard={handleDiscard}
              onStarted={handleStarted}
            />
          ) : (
            <TabRecorderForm
              initialDevices={devices}
              initialDeviceId={selectedDeviceId}
              screenStream={screenStream}
              onDiscard={handleDiscard}
              onStarted={handleStarted}
            />
          )}
        </div>
      </div>
    </div>
  )
}
