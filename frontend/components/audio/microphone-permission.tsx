// frontend/components/audio/microphone-permission.tsx
import React, { useCallback, useEffect, useState } from 'react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Loader2 } from 'lucide-react'

interface MicrophonePermissionProps {
  onPermissionGranted: (devices: AudioDevice[]) => void
  onError: (error: string) => void
}

export interface AudioDevice {
  deviceId: string
  label: string
}

export function MicrophonePermission({
  onPermissionGranted,
  onError,
}: MicrophonePermissionProps) {
  const [permissionDenied, setPermissionDenied] = useState(false)
  const [isRequesting, setIsRequesting] = useState(true)

  const getAudioDevices = useCallback(async () => {
    try {
      const devices = await navigator.mediaDevices.enumerateDevices()
      const audioInputDevices = devices
        .filter((device) => device.kind === 'audioinput')
        .map((device) => ({
          deviceId: device.deviceId,
          label: device.label || `Microphone ${device.deviceId.slice(0, 5)}`,
        }))

      if (audioInputDevices.length > 0) {
        onPermissionGranted(audioInputDevices)
      }
    } catch {
      onError('Error getting audio devices')
      setPermissionDenied(true)
      setIsRequesting(false)
    }
  }, [onError, onPermissionGranted])

  const requestMicrophonePermission = useCallback(async () => {
    setIsRequesting(true)
    setPermissionDenied(false)

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      stream.getTracks().forEach((track) => track.stop())
      await getAudioDevices()
    } catch {
      onError(
        'Microphone permission denied. Please enable it in your browser settings.'
      )
      setPermissionDenied(true)
      setIsRequesting(false)
    }
  }, [getAudioDevices, onError])

  useEffect(() => {
    requestMicrophonePermission()
  }, [requestMicrophonePermission])

  return (
    <div>
      {permissionDenied ? (
        <Alert variant="destructive">
          <AlertDescription>
            Microphone permission denied. Please enable it in your browser
            settings.
          </AlertDescription>
        </Alert>
      ) : (
        <Alert>
          <AlertDescription className="flex items-center">
            {isRequesting && <Loader2 className="mr-2 size-4 animate-spin" />}
            {isRequesting
              ? 'Requesting microphone access...'
              : 'Microphone permission is required to use this feature.'}
          </AlertDescription>
        </Alert>
      )}
      {permissionDenied && (
        <Button onClick={requestMicrophonePermission} className="mt-2">
          Request Microphone Permission
        </Button>
      )}
    </div>
  )
}
