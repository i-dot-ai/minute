import type { Event } from '@sentry/nextjs'

export function redactSearchUrl(value: string): string {
  let url: URL
  try {
    url = new URL(value, 'http://localhost')
  } catch {
    return value
  }
  const search = [
    '/search',
    '/transcriptions/search',
    '/api/proxy/transcriptions/search',
  ].includes(url.pathname)
  const match = url.hash.startsWith('#search-match?')
  if (!search && !match) return value
  if (search) url.search = ''
  if (match) url.hash = ''
  return value.startsWith('/')
    ? `${url.pathname}${url.search}${url.hash}`
    : url.href
}

export function redactSearchTelemetry<T extends Event>(event: T): T {
  const request = event.request
  if (request?.url) {
    const redacted = redactSearchUrl(request.url)
    if (redacted !== request.url) delete request.query_string
    request.url = redacted
  }
  for (const data of [
    request?.headers,
    ...(event.breadcrumbs?.map((breadcrumb) => breadcrumb.data) ?? []),
    ...(event.spans?.map((span) => span.data) ?? []),
  ]) {
    if (!data) continue
    for (const key of [
      'url',
      'from',
      'to',
      'Referer',
      'referer',
      'http.url',
      'http.target',
    ]) {
      if (typeof data[key] === 'string') data[key] = redactSearchUrl(data[key])
    }
  }
  return event
}
