'use client'

import { useLockNavigationContext } from '@/hooks/use-lock-navigation-context'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { ComponentProps } from 'react'

type GuardedLinkProps = ComponentProps<typeof Link>

export const GuardedLink = ({ href, onClick, ...props }: GuardedLinkProps) => {
  const router = useRouter()
  const { requestNavigation } = useLockNavigationContext()

  return (
    <Link
      href={href}
      onClick={(e) => {
        onClick?.(e)
        if (e.defaultPrevented) return
        // Let the browser handle new-tab / modified clicks and external targets.
        if (
          e.metaKey ||
          e.ctrlKey ||
          e.shiftKey ||
          e.altKey ||
          e.button !== 0 ||
          props.target === '_blank'
        ) {
          return
        }
        // Always drive navigation through router.push so Link doesn't navigate
        // in parallel; requestNavigation runs it now or defers it behind the guard.
        e.preventDefault()
        requestNavigation(() => router.push(String(href)))
      }}
      {...props}
    />
  )
}
