'use client'

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import { Button } from '@/components/ui/button'
import { useLockNavigationContext } from '@/hooks/use-lock-navigation-context'
import { Home } from 'lucide-react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'

export const HomeButton = () => {
  const { lockNavigation, setLockNavigation } = useLockNavigationContext()
  const router = useRouter()
  if (lockNavigation) {
    return (
      <AlertDialog>
        <AlertDialogTrigger asChild>
          <Button variant="ghost">
            <Home size="1rem" />
          </Button>
        </AlertDialogTrigger>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              Are you sure you want to leave the page?
            </AlertDialogTitle>
            <AlertDialogDescription>
              You have a recording that has not been uploaded, are you sure you
              want to leave this page? (Your recording will be discarded if you
              do not upload it, or save a local copy.)
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                setLockNavigation(false)
                router.push('/')
              }}
            >
              Continue
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    )
  }

  return (
    <Button asChild variant="ghost">
      <Link href="/">
        <Home size="1rem" />
      </Link>
    </Button>
  )
}
