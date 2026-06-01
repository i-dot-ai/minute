import { cookies } from 'next/headers'
import { redirect } from 'next/navigation'

const SEVEN_DAYS_SECONDS = 7 * 24 * 60 * 60

export async function GET() {
  const cookieStore = cookies()
  cookieStore.delete('X-Amzn-Oidc-Data-0')
  cookieStore.delete('AWSALBAuthNonce')
  cookieStore.set('SESSION_HAS_BEEN_REFRESHED', 'TRUE', {
    maxAge: SEVEN_DAYS_SECONDS,
    httpOnly: true,
    secure: true,
    sameSite: 'lax',
    path: '/',
  })
  redirect('/')
}
