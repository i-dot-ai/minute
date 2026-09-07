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
        const proceeded = requestNavigation(() => router.push(String(href)))
        if (!proceeded) e.preventDefault()
      }}
      {...props}
    />
  )
}
