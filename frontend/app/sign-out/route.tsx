import { cookies } from 'next/headers'
import { redirect } from 'next/navigation'

export async function GET() {
  const clientId = process.env.OIDC_CLIENT_ID || ''
  if (!clientId) {
    console.error('OIDC_CLIENT_ID environment variable is not set')
  }

  const cookieStore = cookies()
  cookieStore.delete('X-Amzn-Oidc-Data-0')
  cookieStore.delete('AWSALBAuthNonce')

  const ssoSignOutUrl = `https://sso.service.security.gov.uk/sign-out?to_client=${encodeURIComponent(clientId)}`
  redirect(ssoSignOutUrl)
}
