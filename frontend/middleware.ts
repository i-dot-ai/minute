import { API_PROXY_PATH } from '@/lib/api-proxy-path'
import { NextRequest, NextResponse } from 'next/server'
import { type UserAuthorisationResult } from '@i-dot-ai-npm/utilities-auth'
import { parseAuthToken } from './utils/auth'

// Define paths that should be public (no authorisation required)
const PUBLIC_PATHS = [
  '/unauthorised',
  '/health',
  '/generic-error',
  '/monitoring',
  '/privacy',
  '/support',
  '/sign-out',
]

function applySecurityHeaders(req: NextRequest) {
  const nonce = Buffer.from(crypto.randomUUID()).toString('base64')
  const isDev =
    process.env.NODE_ENV === 'development' || process.env.NODE_ENV === 'test'

  const csp = [
    "default-src 'none'",
    `script-src 'self' 'nonce-${nonce}' 'strict-dynamic'${isDev ? " 'unsafe-eval'" : ''}`,
    "style-src 'self' 'unsafe-inline'",
    "font-src 'self'",
    "img-src 'self' data:",
    `media-src 'self' blob: https://*.s3.amazonaws.com https://*.s3.${process.env.AWS_REGION ?? 'eu-west-2'}.amazonaws.com`,
    `connect-src 'self' https://eu.i.posthog.com https://*.s3.amazonaws.com https://*.s3.${process.env.AWS_REGION ?? 'eu-west-2'}.amazonaws.com`,
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "object-src 'none'",
  ].join('; ')

  const requestHeaders = new Headers(req.headers)
  requestHeaders.set('x-nonce', nonce)
  requestHeaders.set('content-security-policy', csp)
  requestHeaders.set('x-pathname', req.nextUrl.pathname)

  const res = NextResponse.next({ request: { headers: requestHeaders } })
  res.headers.set('content-security-policy', csp)
  return res
}

export async function middleware(req: NextRequest) {
  try {
    const { pathname } = req.nextUrl

    // Check if the requested path is public
    if (PUBLIC_PATHS.some((path) => pathname.startsWith(path))) {
      return applySecurityHeaders(req)
    }

    // Proxy directly to the backend for API requests
    if (pathname.startsWith(API_PROXY_PATH)) {
      const url = new URL(req.url)
      const newPath = `${url.pathname.replace(API_PROXY_PATH, '')}`
      const newUrl = process.env.BACKEND_HOST + newPath + url.search + url.hash
      return NextResponse.rewrite(newUrl, { request: req })
    }

    // Authorise user for frontend access
    let authResult: UserAuthorisationResult | null = null

    if (process.env.ENVIRONMENT !== 'local') {
      const token = req.headers.get('x-amzn-oidc-data')

      if (!token) {
        console.error(
          `No auth token found in headers when accessing ${pathname}`
        )
        return redirectToUnauthorised(req)
      }

      authResult = await parseAuthToken(token)
    } else {
      authResult = {
        email: 'test@test.co.uk',
        isAuthorised: true,
        authReason: 'LOCAL_TESTING',
      }
    }
    if (authResult?.isAuthorised !== true) {
      if (authResult?.authReason === 'TOKEN_EXPIRED') {
        return redirectToSignOut(req)
      }
      console.error(`User is not authorised to access ${pathname}`)
      return redirectToUnauthorised(req)
    }

    console.info(
      `User ${authResult.email} authorisation result: ${authResult.isAuthorised}`
    )
    return applySecurityHeaders(req)
  } catch (error) {
    console.error('Error authorising token:', error)
    return redirectToGenericError(req)
  }
}

function redirectToUnauthorised(req: NextRequest) {
  const url = req.nextUrl.clone()
  url.pathname = '/unauthorised'
  return NextResponse.redirect(url)
}

function redirectToGenericError(req: NextRequest) {
  const url = req.nextUrl.clone()
  url.pathname = '/generic-error'
  return NextResponse.redirect(url)
}
function redirectToSignOut(req: NextRequest) {
  const url = req.nextUrl.clone()
  url.pathname = '/sign-out'
  return NextResponse.redirect(url)
}
// Configure which paths this middleware should run on
export const config = {
  matcher: [
    // Match all paths except those starting with excluded paths
    // You can customize this as needed
    '/((?!_next/static|_next/image|favicon.ico|api/health).*)',
  ],
}
