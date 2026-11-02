import type { HourlyProcessingStatus } from '@/lib/processing-status'
import { mocked } from './mocked'

// Shared across authorised users, not keyed by their authentication token. Cached for 1 minute like the backend.
// shortcut: cache is per frontend instance; use a shared store if replicas need one global snapshot.
let cached: { data: HourlyProcessingStatus; expiresAt: number } | undefined
let pending: Promise<HourlyProcessingStatus> | undefined

async function loadStatus(request: Request): Promise<HourlyProcessingStatus> {
  const token = request.headers.get('x-amzn-oidc-data')
  const response = await fetch(`${process.env.BACKEND_HOST}/status/hourly`, {
    headers: token ? { 'x-amzn-oidc-data': token } : {},
    cache: 'no-store',
    signal: AbortSignal.timeout(25_000),
  })
  if (!response.ok)
    throw new Error(`Hourly status request failed: ${response.status}`)
  const data: HourlyProcessingStatus = await response.json()
  cached = { data, expiresAt: Date.now() + 60_000 }
  return data
}

export async function GET(request: Request) {
  // /status?mocked shows sample data with a few bad hours, for demos.
  if (new URL(request.url).searchParams.has('mocked'))
    return Response.json(mocked)
  try {
    if (!cached || Date.now() >= cached.expiresAt) {
      pending ??= loadStatus(request).finally(() => {
        pending = undefined
      })
      await pending
    }
    return Response.json(cached!.data, {
      headers: { 'Cache-Control': 'private, no-store' },
    })
  } catch (error) {
    console.error('Failed to fetch hourly processing status', error)
    return Response.json(
      { detail: 'Processing status is temporarily unavailable' },
      { status: 503 }
    )
  }
}
