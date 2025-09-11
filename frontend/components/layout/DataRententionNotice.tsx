'use client'

import { getUserUsersMeGetOptions } from '@/lib/client/@tanstack/react-query.gen'
import { useQuery } from '@tanstack/react-query'
import { AlertCircle } from 'lucide-react'

export const DataRetentionNotice = () => {
  const { data: user, isLoading } = useQuery({ ...getUserUsersMeGetOptions() })
  if (isLoading || !user) {
    return null
  }
  if (!user.strict_data_retention) {
    return null
  }
  return (
    <div className="mx-auto w-full max-w-3xl">
      <div
        style={{
          backgroundColor: '#fff3cd', // A light yellow, common for warnings
          color: '#856404', // Darker text for contrast
          padding: '1rem',
          border: '1px solid #ffeeba',
          borderRadius: '0.25rem',
          display: 'flex',
          marginBottom: '1rem',
          alignItems: 'center',
        }}
        role="alert"
      >
        <AlertCircle size={40} style={{ marginRight: '0.75rem' }} />
        <span>
          <strong>Data Retention Notice:</strong> Due to your organisation&#39;s
          retention policy, transcripts and summaries will be retained by Minute
          for 24 hours unless explicitly deleted. Audio recordings are never
          retained.
        </span>
      </div>
    </div>
  )
}
