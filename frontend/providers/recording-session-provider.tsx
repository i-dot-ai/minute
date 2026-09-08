'use client'

import { AudioDevice } from '@/components/audio/microphone-permission'
import { Template } from '@/types/templates'
import { ReactNode, createContext, useContext, useState } from 'react'

export type RecordingMode = 'in-person' | 'virtual-meeting' | 'upload-file'

type RecordingSessionValue = {
  mode: RecordingMode | null
  setMode: (mode: RecordingMode | null) => void
  screenStream: MediaStream | null
  setScreenStream: (stream: MediaStream | null) => void
  uploadFile: File | null
  setUploadFile: (file: File | null) => void
  uploadTemplate: Template | null
  setUploadTemplate: (template: Template | null) => void
  uploadAgenda: string | undefined
  setUploadAgenda: (agenda: string | undefined) => void
  devices: AudioDevice[]
  setDevices: (devices: AudioDevice[]) => void
  selectedDeviceId: string
  setSelectedDeviceId: (id: string) => void
  reset: () => void
}

const RecordingSessionContext = createContext<RecordingSessionValue | null>(
  null
)

export function RecordingSessionProvider({
  children,
}: {
  children: ReactNode
}) {
  const [mode, setMode] = useState<RecordingMode | null>(null)
  const [screenStream, setScreenStream] = useState<MediaStream | null>(null)
  const [uploadFile, setUploadFile] = useState<File | null>(null)
  const [uploadTemplate, setUploadTemplate] = useState<Template | null>(null)
  const [uploadAgenda, setUploadAgenda] = useState<string | undefined>(
    undefined
  )
  const [devices, setDevices] = useState<AudioDevice[]>([])
  const [selectedDeviceId, setSelectedDeviceId] = useState('')

  const reset = () => {
    setMode(null)
    setScreenStream(null)
    setUploadFile(null)
    setUploadTemplate(null)
    setUploadAgenda(undefined)
  }

  return (
    <RecordingSessionContext.Provider
      value={{
        mode,
        setMode,
        screenStream,
        setScreenStream,
        uploadFile,
        setUploadFile,
        uploadTemplate,
        setUploadTemplate,
        uploadAgenda,
        setUploadAgenda,
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
