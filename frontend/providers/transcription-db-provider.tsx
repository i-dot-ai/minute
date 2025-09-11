'use client'

import {
  createContext,
  ReactNode,
  useCallback,
  useContext,
  useEffect,
  useState,
} from 'react'

// Define the type for recording items
export type RecordingDbItem = {
  recording_id: string
  updated_at: Date
  blob: Blob
}

// Define the context type
interface RecordingDbContextType {
  addRecording: (blob: Blob) => Promise<string | undefined>
  removeRecording: (id: string) => Promise<void>
  getRecording: (id: string) => Promise<RecordingDbItem | undefined>
  updateRecording: (id: string, blob: Blob) => Promise<void>
  listRecordings: () => Promise<RecordingDbItem[]>
}

// Create the context
const RecordingDbContext = createContext<RecordingDbContextType | undefined>(
  undefined
)

// Provider component
interface RecordingDbProviderProps {
  children: ReactNode
}

export function RecordingDbProvider({ children }: RecordingDbProviderProps) {
  const [db, setDb] = useState<IDBDatabase | null>(null)

  useEffect(() => {
    const request = window.indexedDB.open('MinuteDB', 1)
    request.onsuccess = (event) => {
      setDb((event.target as IDBOpenDBRequest)?.result || null)
    }
    // This event is only implemented in recent browsers
    request.onupgradeneeded = (event) => {
      // Save the IDBDatabase interface
      const db = (event.target as IDBOpenDBRequest).result

      // Create an objectStore for this database
      db.createObjectStore('recordings', {
        keyPath: 'recording_id',
      })
    }
  }, [])

  const addRecording = useCallback(
    (blob: Blob): Promise<string | undefined> => {
      return new Promise((resolve, reject) => {
        if (!db) return reject(new Error('Database not found'))
        const transaction = db.transaction('recordings', 'readwrite')
        const objectStore = transaction.objectStore('recordings')
        const recording_id = crypto.randomUUID()
        objectStore.add({
          recording_id,
          blob,
          updated_at: new Date(),
        })
        transaction.oncomplete = () => {
          resolve(recording_id)
        }
        transaction.onerror = () => {
          reject(new Error('Error adding recording'))
        }
      })
    },
    [db]
  )

  const removeRecording = useCallback(
    (id: string): Promise<void> => {
      return new Promise((resolve, reject) => {
        if (!db) return reject(new Error('Database not found'))
        const transaction = db.transaction('recordings', 'readwrite')
        const objectStore = transaction.objectStore('recordings')
        objectStore.delete(id)
        transaction.oncomplete = () => {
          resolve()
        }
        transaction.onerror = () => {
          reject(new Error('Error removing recording'))
        }
      })
    },
    [db]
  )

  const getRecording = useCallback(
    (id: string): Promise<RecordingDbItem | undefined> => {
      return new Promise((resolve, reject) => {
        if (!db) return reject(new Error('Database not found'))
        const transaction = db
          .transaction('recordings', 'readonly')
          .objectStore('recordings')
          .get(id)
        transaction.onsuccess = (event) => {
          console.log('success', event)
          resolve((event.target as IDBRequest)?.result || undefined)
        }
        transaction.onerror = (ev) => {
          console.log('failed', ev)
          reject(new Error('Error getting recording'))
        }
      })
    },
    [db]
  )

  const updateRecording = useCallback(
    (id: string, blob: Blob): Promise<void> => {
      return new Promise((resolve, reject) => {
        if (!db) return reject(new Error('Database not found'))
        const transaction = db.transaction('recordings', 'readwrite')
        const objectStore = transaction.objectStore('recordings')
        objectStore.put({
          recording_id: id,
          blob: blob,
          updated_at: new Date(),
        })
        transaction.oncomplete = () => {
          resolve()
        }
        transaction.onerror = () => {
          reject(new Error('Error updating recording'))
        }
      })
    },
    [db]
  )

  const listRecordings = useCallback((): Promise<RecordingDbItem[]> => {
    return new Promise((resolve, reject) => {
      if (!db) return reject(new Error('Database not found'))
      const transaction = db.transaction('recordings', 'readonly')
      const objectStore = transaction.objectStore('recordings')
      const request = objectStore.getAll()
      request.onsuccess = () => {
        resolve(request.result || [])
      }
      request.onerror = () => {
        reject(new Error('Error listing recordings'))
      }
    })
  }, [db])

  const value: RecordingDbContextType = {
    addRecording,
    removeRecording,
    getRecording,
    updateRecording,
    listRecordings,
  }

  return (
    <RecordingDbContext.Provider value={value}>
      {children}
    </RecordingDbContext.Provider>
  )
}

// Hook to use the recording database context
export function useRecordingDb() {
  const context = useContext(RecordingDbContext)
  if (context === undefined) {
    throw new Error('useRecordingDb must be used within a RecordingDbProvider')
  }
  return context
}
