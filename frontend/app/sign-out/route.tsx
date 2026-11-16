import { cookies, headers } from 'next/headers'
import { redirect } from 'next/navigation'

export async function GET() {
  const clientId = process.env.OIDC_CLIENT_ID || ''
  if (!clientId) {
    console.error('OIDC_CLIENT_ID environment variable is not set')
  }

  // Only clear cookies on an explicit sign-out, not on a prefetch
  const isPrefetch = (await headers()).get('Next-Router-Prefetch') === '1'

  if (!isPrefetch) {
    const cookieStore = await cookies()
    cookieStore.delete('X-Amzn-Oidc-Data-0')
    cookieStore.delete('AWSALBAuthNonce')
  }

  const ssoSignOutUrl = `https://sso.service.security.gov.uk/sign-out?to_client=${encodeURIComponent(clientId)}`
  redirect(ssoSignOutUrl)
}
