'use client'

import { MicRecorderForm } from '@/components/audio/mic-recorder'
import { TabRecorderForm } from '@/components/audio/tab-recorder/tab-recorder'
import { AudioUploadForm } from '@/components/audio/AudioUploadForm'
import { RestartTourButton } from '@/components/onboarding/restart-tour-button'
import { PosthogBanner } from '@/components/posthog-banner'
import UrlMigrationBanner from '@/components/url-migration-banner'
import { useIsOldUrl } from '@/hooks/use-is-old-url'
import { AudioDevice } from '@/components/audio/microphone-permission'
import { Mic, Video, Upload } from 'lucide-react'
import { useState, useEffect } from 'react'

type RecordingMode = 'in-person' | 'virtual-meeting' | 'upload-file'

const buttonLabels: Record<RecordingMode, string> = {
  'in-person': 'Start recording',
  'virtual-meeting': 'Start recording',
  'upload-file': 'Upload a file',
}

export default function Home() {
  const isOldUrl = useIsOldUrl()
  const [mode, setMode] = useState<RecordingMode>('in-person')
  const [started, setStarted] = useState(false)
  const [devices, setDevices] = useState<AudioDevice[]>([])
  const [selectedDeviceId, setSelectedDeviceId] = useState<string>('')

  useEffect(() => {
    const init = async () => {
      try {
        let granted = false
        try {
          const status = await navigator.permissions.query({
            name: 'microphone' as PermissionName,
          })
          granted = status.state === 'granted'
        } catch (error) {
          console.error(error)
          console.error(
            'Permissions API / "microphone" query unsupported (e.g. Safari) — treat as not granted so we still resolve real device IDs below.'
          )
        }

        // Only activate the mic if permission hasn't already been granted.
        // When granted, enumerateDevices alone returns real labels + IDs.
        if (!granted) {
          const stream = await navigator.mediaDevices.getUserMedia({
            audio: true,
          })
          stream.getTracks().forEach((t) => t.stop())
        }

        const all = await navigator.mediaDevices.enumerateDevices()
        const audioDevices = all
          .filter((d) => d.kind === 'audioinput')
          .map((d) => ({
            deviceId: d.deviceId,
            label: d.label || `Microphone ${d.deviceId.slice(0, 5)}`,
          }))
        setDevices(audioDevices)
        if (audioDevices.length) setSelectedDeviceId(audioDevices[0].deviceId)
      } catch (error) {
        console.error(error)
      }
    }
    init()
  }, [])

  return (
    <>
      <div className="govuk-width-container govuk-main-wrapper">
        {isOldUrl ? <UrlMigrationBanner /> : <PosthogBanner />}
        <div className="govuk-grid-row">
          <div className="govuk-grid-column-full">
            <h1 className="govuk-heading-l">Record a meeting</h1>
            <p className="govuk-hint">
              Please ensure that all participants are aware that they have
              been recorded. Suitable up to{' '}
              <strong>OFFICIAL SENSITIVE</strong>.
            </p>
            {!started ? (
              <div className="govuk-form-group">
                <fieldset
                  className="govuk-fieldset govuk-!-margin-top-9 h-55"
                  aria-describedby="recordMeeting-hint"
                >
                  <div
                    className="govuk-radios govuk-radios--inline flex"
                    data-module="govuk-radios"
                  >
                    <div className="govuk-radios__item new-recording__radio-item flex-1">
                      <input
                        className="govuk-radios__input"
                        id="in-person"
                        name="recordMeeting"
                        type="radio"
                        value="in-person"
                        checked={mode === 'in-person'}
                        onChange={() => setMode('in-person')}
                      />
                      <label
                        className="govuk-label govuk-radios__label"
                        htmlFor="in-person"
                      >
                        <Mic className="mb-2 size-7" />
                        <h2 className="govuk-heading-m">In person</h2>
                        <p className="govuk-body">
                          Record audio from this device's microphone.
                        </p>
                      </label>
                    </div>
                    <div className="govuk-radios__item new-recording__radio-item flex-1">
                      <input
                        className="govuk-radios__input"
                        id="virtual-meeting"
                        name="recordMeeting"
                        type="radio"
                        value="virtual-meeting"
                        checked={mode === 'virtual-meeting'}
                        onChange={() => setMode('virtual-meeting')}
                      />
                      <label
                        className="govuk-label govuk-radios__label"
                        htmlFor="virtual-meeting"
                      >
                        <Video className="mb-2 size-7" />
                        <h2 className="govuk-heading-m">Virtual meeting</h2>
                        <p className="govuk-body">
                          Join your call silently — not visible to other
                          attendees.
                        </p>
                      </label>
                    </div>
                    <div className="govuk-radios__item new-recording__radio-item flex-1">
                      <input
                        className="govuk-radios__input"
                        id="upload-file"
                        name="recordMeeting"
                        type="radio"
                        value="upload-file"
                        checked={mode === 'upload-file'}
                        onChange={() => setMode('upload-file')}
                      />
                      <label
                        className="govuk-label govuk-radios__label"
                        htmlFor="upload-file"
                      >
                        <Upload className="mb-2 size-7" />
                        <h2 className="govuk-heading-m">Upload a file</h2>
                        <p className="govuk-body">
                          Use a recording you already have.
                        </p>
                      </label>
                    </div>
                  </div>
                </fieldset>
                {mode === 'upload-file' ? (
                  <AudioUploadForm />
                ) : (
                  <>
                    <div className="govuk-form-group">
                      <label
                        className="govuk-label"
                        htmlFor="microphone"
                      >
                        Choose microphone
                      </label>
                      <select
                        className="govuk-select"
                        id="microphone"
                        name="microphone"
                        value={selectedDeviceId}
                        onChange={(e) => setSelectedDeviceId(e.target.value)}
                      >
                        {devices.length > 0 ? (
                          devices.map((d) => (
                            <option key={d.deviceId} value={d.deviceId}>
                              {d.label}
                            </option>
                          ))
                        ) : (
                          <option value="">
                            Requesting microphone access...
                          </option>
                        )}
                      </select>
                    </div>
                  </>
                )}
                <button
                  className="govuk-button govuk-button--start govuk-!-margin-top-6"
                  data-module="govuk-button"
                  onClick={() => setStarted(true)}
                >
                  {buttonLabels[mode]}
                  <svg
                    className="govuk-button__start-icon"
                    xmlns="http://www.w3.org/2000/svg"
                    width="17.5"
                    height="19"
                    viewBox="0 0 33 40"
                    role="presentation"
                    focusable="false"
                  >
                    <path
                      fill="currentColor"
                      d="M0 0h13l20 20-20 20H0l20-20z"
                    />
                  </svg>
                </button>
              </div>
            ) : (
              <>
                {mode === 'in-person' && (
                  <MicRecorderForm
                    initialDevices={devices}
                    initialDeviceId={selectedDeviceId}
                    onDiscard={() => setStarted(false)}
                  />
                )}
                {mode === 'virtual-meeting' && <TabRecorderForm />}
                {mode === 'upload-file' && <AudioUploadForm />}
              </>
            )}
          </div>
        </div>
      </div>
    </>
  )
}
