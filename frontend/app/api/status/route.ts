import type { ProcessingStatus } from '@/lib/processing-status'

// Shared across authorised users, not keyed by their authentication token.
// shortcut: cache is per frontend instance; use a shared store if replicas need one global snapshot.
let cached: { data: ProcessingStatus; expiresAt: number } | undefined
let pending: Promise<ProcessingStatus> | undefined

async function loadStatus(request: Request): Promise<ProcessingStatus> {
  const token = request.headers.get('x-amzn-oidc-data')
  const response = await fetch(
    `${process.env.BACKEND_HOST}/status?horizon=10m`,
    {
      headers: token ? { 'x-amzn-oidc-data': token } : {},
      cache: 'no-store',
      signal: AbortSignal.timeout(15_000),
    }
  )
  if (!response.ok) throw new Error(`Status request failed: ${response.status}`)
  const data: ProcessingStatus = await response.json()
  cached = { data, expiresAt: Date.now() + 60_000 }
  return data
}

export async function GET(request: Request) {
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
    console.error('Failed to fetch processing status', error)
    return Response.json(
      { detail: 'Processing status is temporarily unavailable' },
      { status: 503 }
    )
  }
}
