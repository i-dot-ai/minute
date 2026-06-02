import { cookies } from 'next/headers'
import { redirect } from 'next/navigation'

export async function GET() {
  const cookieStore = cookies()
  cookieStore.delete('X-Amzn-Oidc-Data-0')
  cookieStore.delete('AWSALBAuthNonce')
  redirect('/')
}
