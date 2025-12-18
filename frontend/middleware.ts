import { API_PROXY_PATH } from '@/providers/TanstackQueryProvider'
import { NextRequest, NextResponse } from 'next/server'
import { type UserAuthorisationResult } from '@i-dot-ai-npm/utilities'
import { parseAuthToken } from './utils/auth'

// Define paths that should be public (no authorisation required)
const PUBLIC_PATHS = [
  '/unauthorised',
  '/health',
  '/generic-error',
  '/monitoring',
  '/privacy',
  '/support',
]

export async function middleware(req: NextRequest) {
  try {
    const { pathname } = req.nextUrl

    // Check if the requested path is public
    if (PUBLIC_PATHS.some((path) => pathname.startsWith(path))) {
      return NextResponse.next()
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
      console.error(`User is not authorised to access ${pathname}`)
      return redirectToUnauthorised(req)
    }

    console.info(
      `User ${authResult.email} authorisation result: ${authResult.isAuthorised}`
    )

    return NextResponse.next()
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

// Configure which paths this middleware should run on
export const config = {
  matcher: [
    // Match all paths except those starting with excluded paths
    // You can customize this as needed
    '/((?!_next/static|_next/image|favicon.ico|api/health).*)',
  ],
}
