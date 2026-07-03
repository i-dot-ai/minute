'use client'

import { AudioDevice } from '@/components/audio/microphone-permission'
import { ReactNode, createContext, useContext, useState } from 'react'

export type RecordingMode = 'in-person' | 'virtual-meeting'

type RecordingSessionValue = {
  mode: RecordingMode | null
  setMode: (mode: RecordingMode | null) => void
  screenStream: MediaStream | null
  setScreenStream: (stream: MediaStream | null) => void
  devices: AudioDevice[]
  setDevices: (devices: AudioDevice[]) => void
  selectedDeviceId: string
  setSelectedDeviceId: (id: string) => void
  reset: () => void
}

const RecordingSessionContext = createContext<RecordingSessionValue | null>(null)

export function RecordingSessionProvider({ children }: { children: ReactNode }) {
  const [mode, setMode] = useState<RecordingMode | null>(null)
  const [screenStream, setScreenStream] = useState<MediaStream | null>(null)
  const [devices, setDevices] = useState<AudioDevice[]>([])
  const [selectedDeviceId, setSelectedDeviceId] = useState('')

  const reset = () => {
    setMode(null)
    setScreenStream(null)
  }

  return (
    <RecordingSessionContext.Provider
      value={{
        mode,
        setMode,
        screenStream,
        setScreenStream,
        devices,
        setDevices,
        selectedDeviceId,
        setSelectedDeviceId,
        reset,
      }}
    >
      {children}
    </RecordingSessionContext.Provider>
  )
}

export function useRecordingSession() {
  const context = useContext(RecordingSessionContext)
  if (!context) {
    throw new Error(
      'useRecordingSession must be used within a RecordingSessionProvider'
    )
  }
  return context
}
