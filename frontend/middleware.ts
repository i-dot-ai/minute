import { isAuthorisedUser } from '@/lib/auth'
import { API_PROXY_PATH } from '@/providers/TanstackQueryProvider'
import { NextRequest, NextResponse } from 'next/server'

// Define paths that should be public (no authorisation required)
const PUBLIC_PATHS = ['/unauthorised', '/health']

const TEST_AUTHORISATION_JWT =
  'eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOiIxNzM5ODk2MTk5IiwiaWF0IjoiMTczOTg5NTg5OSIsImF1dGhfdGltZSI6IjE3Mzk4OTM1MjkiLCJqdGkiOiIyYmVmOGI1ZS0yOGY0LTQ2OWQtYWQ2My1lZjJlNDgxNzliODYiLCJpc3MiOiJodHRwczovL2F1dGgub2JmdXNjYXRlZC50ZXN0LmRvbWFpbi5nb3YudWsvcmVhbG1zL29iZnVzY2F0ZWQiLCJhdWQiOiJhY2NvdW50Iiwic3ViIjoiYmMzNzNkZTQtNDAyMi00NmIyLTgxNTEtZjA0NjEzNzhlOWNiIiwidHlwIjoiQmVhcmVyIiwiYXpwIjoibWludXRlIiwic2lkIjoiYzM2NmE5ZmUtMDNiNC00MjIxLWI0ZWItOTE0MzMzNWFhNjUyIiwiYWNyIjoiMSIsImFsbG93ZWQtb3JpZ2lucyI6WyJodHRwczovL21pbnV0ZS1kZXYub2JmdXNjYXRlZC50ZXN0LmRvbWFpbi5nb3YudWsiXSwicmVhbG1fYWNjZXNzIjp7InJvbGVzIjpbIm1pbnV0ZSJdfSwicmVzb3VyY2VfYWNjZXNzIjp7ImFjY291bnQiOnsicm9sZXMiOlsibWFuYWdlLWFjY291bnQiLCJtYW5hZ2UtYWNjb3VudC1saW5rcyIsInZpZXctcHJvZmlsZSJdfX0sInNjb3BlIjoib3BlbmlkIHByb2ZpbGUgZW1haWwiLCJlbWFpbF92ZXJpZmllZCI6InRydWUiLCJwcmVmZXJyZWRfdXNlcm5hbWUiOiJ0ZXN0QHRlc3QuY28udWsiLCJlbWFpbCI6InRlc3RAdGVzdC5jby51ayJ9.a-l8CBKJjghdCejqdMBv4crgDyj2xxeFk-NPNFfOtJ4QoqiROkEkHA7f-5YQsZfeW4NdbX5yN-NV9fhVBJbWvVS2Wzgt_0U1Seov79gmkDWieKp-XJKuf7MbPr149R3emdZERUQy_etYyLFgo4eVH79DkB3EJbYxXA3WyxKBq3v600Rl5SXz3Hjsv6ZFsf2feJVpC3dIb_jqFZI-dz9bZznJBTqdaAY3lKo431w4WfJfhXJVLxCS2oilodpV3kMkAyIrbOeBD60PLodU9HoHCdX9G57fEFEg89MMs8FitMPH8ao6YuR917gbY_aa02sJgEXhWZ9_iwFzFm2Lq5xCkg'

export async function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl

  // Check if the requested path is public
  if (PUBLIC_PATHS.some((path) => pathname.startsWith(path))) {
    return NextResponse.next()
  }

  try {
    let token

    if (process.env.ENVIRONMENT == 'local') {
      token = TEST_AUTHORISATION_JWT
    } else {
      token = req.headers.get('x-amzn-oidc-accesstoken')
    }

    if (!token) {
      console.error(`No auth token found in headers when accessing ${pathname}`)
      return redirectToUnauthorised(req)
    }

    if (!(await isAuthorisedUser(token))) {
      return redirectToUnauthorised(req)
    }

    if (pathname.startsWith(API_PROXY_PATH)) {
      const url = new URL(req.url)
      const newPath = `${url.pathname.replace(API_PROXY_PATH, '')}`
      const newUrl = process.env.BACKEND_HOST + newPath + url.search + url.hash
      return NextResponse.rewrite(newUrl, { request: req })
    }

    return NextResponse.next()
  } catch (error) {
    console.error('Error authorising token:', error)
    return redirectToUnauthorised(req)
  }
}

function redirectToUnauthorised(req: NextRequest) {
  const url = req.nextUrl.clone()
  url.pathname = '/unauthorised'
  return NextResponse.redirect(url)
}

// Configure which paths this middleware should run on
export const config = {
  matcher: [
    // Match all paths except those starting with excluded paths
    // You can customize this as needed
    '/((?!unauthorised|_next/static|_next/image|favicon.ico|api/health).*)',
  ],
}
