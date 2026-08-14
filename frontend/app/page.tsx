'use client'

import { AudioUploadForm } from '@/components/audio/AudioUploadForm'
import { PosthogBanner } from '@/components/posthog-banner'
import { useIsOldUrl } from '@/hooks/use-is-old-url'
import { AudioDevice } from '@/components/audio/microphone-permission'
import { useRecordingSession } from '@/providers/recording-session-provider'
import { Mic, Video, Upload } from 'lucide-react'
import { useRouter } from 'next/navigation'
import { useState, useEffect } from 'react'
import UrlMigrationBanner from '@/components/url-migration-banner'

type RecordingMode = 'in-person' | 'virtual-meeting' | 'upload-file'

export default function Home() {
  const isOldUrl = useIsOldUrl()
  const router = useRouter()
  const session = useRecordingSession()
  const [mode, setMode] = useState<RecordingMode>('in-person')
  const [started, setStarted] = useState(false)
  const [devices, setDevices] = useState<AudioDevice[]>([])
  const [selectedDeviceId, setSelectedDeviceId] = useState<string>('')
  const [micDenied, setMicDenied] = useState(false)

  useEffect(() => {
    const init = async () => {
      try {
        let granted = false
        try {
          const status = await navigator.permissions.query({
            name: 'microphone' as PermissionName,
          })
          granted = status.state === 'granted'
          if (status.state === 'denied') {
            setMicDenied(true)
            return
          }
        } catch (error) {
          console.error(error)
          console.error(
            'Permissions API / "microphone" query unsupported (e.g. Safari) — treat as not granted so we still resolve real device IDs below.'
          )
        }

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
        setMicDenied(false)
      } catch (error) {
        console.error(error)
        if (error instanceof DOMException && error.name === 'NotAllowedError') {
          setMicDenied(true)
        }
      }
    }
    init()
  }, [])

  const handleStart = async () => {
    if (mode === 'upload-file') {
      setStarted(true)
      return
    }

    if (mode === 'virtual-meeting') {
      try {
        const stream = await navigator.mediaDevices.getDisplayMedia({
          video: true,
          audio: true,
        })
        session.setScreenStream(stream)
      } catch (error) {
        console.warn('Screen share cancelled or unavailable', error)
        return
      }
    }

    session.setDevices(devices)
    session.setSelectedDeviceId(selectedDeviceId)
    session.setMode(mode)
    router.push('/new')
  }

  return (
    <div className="govuk-width-container govuk-main-wrapper">
      {isOldUrl ? <UrlMigrationBanner /> : <PosthogBanner />}
      <div className="govuk-grid-row">
        <div className="govuk-grid-column-full">
          <h1 className="govuk-heading-l govuk-!-margin-bottom-3">
            Record a meeting
          </h1>
          <p className="govuk-body govuk-!-margin-bottom-2">
            Choose how to capture this meeting.
          </p>
          <p className="govuk-body govuk-!-margin-bottom-5">
            Please ensure that all participants are aware that they have been
            recorded. Suitable up to <strong>OFFICIAL SENSITIVE</strong>.
          </p>
          {started ? (
            <AudioUploadForm />
          ) : (
            <>
              <div className="govuk-form-group">
                <fieldset
                  className="govuk-fieldset"
                  aria-describedby="recordMeeting-hint"
                >
                  <div
                    className="govuk-radios govuk-radios--inline govuk-radios--small govuk-radios--cards"
                    data-module="govuk-radios"
                  >
                    <div className="govuk-radios__item">
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
                        <Mic className="size-7" />
                        <h2 className="govuk-heading-m">In person</h2>
                        <p className="govuk-body">
                          Record audio from this device&apos;s microphone.
                        </p>
                      </label>
                    </div>
                    <div
                      className="govuk-radios__item"
                      id="virtual-meeting-card"
                    >
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
                        <Video className="size-7" />
                        <h2 className="govuk-heading-m">Virtual meeting</h2>
                        <p className="govuk-body">
                          Record your screen and device audio.
                        </p>
                      </label>
                    </div>
                    <div className="govuk-radios__item" id="upload-file-card">
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
                        <Upload className="size-7" />
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
                    {mode === 'virtual-meeting' && (
                      <div
                        className="govuk-!-padding-5 govuk-!-margin-bottom-2 govuk-!-margin-top-4 bg-[#f3f3f3]"
                        id="virtual-meeting-before-start"
                      >
                        <h2 className="govuk-heading-s">Before you start</h2>
                        <ol className="govuk-list govuk-list--number govuk-!-margin-bottom-0">
                          <li>Start Minute</li>
                          <li>
                            Join your meeting (Teams, Zoom, or Google Meet).
                          </li>
                          <li>
                            When the browser asks to share: Share your{' '}
                            <strong>Tab</strong> (Mac) or{' '}
                            <strong>Entire Screen</strong> (Windows), then tick{' '}
                            <strong>Share audio</strong>.
                          </li>
                        </ol>
                      </div>
                    )}
                    <div
                      className="govuk-form-group govuk-!-margin-top-7 govuk-!-margin-bottom-6 sm:flex sm:items-center sm:gap-2"
                      id="tour-select-microphone"
                    >
                      <label className="govuk-label" htmlFor="microphone">
                        Select microphone:
                      </label>
                      <select
                        className="govuk-select govuk-select--subtle"
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
                    {micDenied && (
                      <div
                        role="alert"
                        className="govuk-!-padding-4 govuk-!-margin-bottom-4 bg-[#e59a9a]"
                      >
                        <div className="govuk-warning-text">
                          <span
                            className="govuk-warning-text__icon"
                            aria-hidden="true"
                          >
                            !
                          </span>
                          <strong className="govuk-warning-text__text">
                            <span className="govuk-visually-hidden">
                              Warning
                            </span>
                            There is a problem.
                          </strong>
                        </div>
                        <p className="govuk-body govuk-!-margin-bottom-0">
                          Microphone access has not been given. Please enable it
                          in your browser settings and try again.
                        </p>
                      </div>
                    )}
                    <button
                      className="govuk-button govuk-button--start"
                      data-module="govuk-button"
                      disabled={micDenied}
                      onClick={handleStart}
                    >
                      Start recording
                    </button>
                    {mode === 'virtual-meeting' && (
                      <details
                        className="govuk-details"
                        id="virtual-meeting-audio-not-picking-up"
                      >
                        <summary className="govuk-details__summary">
                          <span className="govuk-details__summary-text">
                            Audio or screen share not picking up? Check system
                            settings
                          </span>
                        </summary>
                        <div className="govuk-details__text">
                          <h2 className="govuk-heading-s">MacOS</h2>
                          <p className="govuk-body">
                            Go to{' '}
                            <strong>
                              System Settings → Privacy & Security → Screen
                              Recording
                            </strong>{' '}
                            and ensure your browser is listed and enabled. Then
                            check <strong>Sound → Input</strong> and confirm the
                            correct microphone is selected.
                          </p>
                          <h2 className="govuk-heading-s">Windows</h2>
                          <p className="govuk-body">
                            Go to{' '}
                            <strong>Settings → Privacy → Microphone</strong> and
                            confirm your browser has access. Check{' '}
                            <strong>Sound → Input</strong> to confirm the
                            correct device is selected.
                          </p>
                        </div>
                      </details>
                    )}
                  </>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
