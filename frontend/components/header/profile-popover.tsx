'use client'

import { LogOut, User, Settings } from 'lucide-react'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { useEffect, useState } from 'react'
import { GuardedLink } from '@/components/navigation/guarded-link'
import ProfileAvatar from '@/components/profile-avatar'
import { getUserUsersMeGetOptions } from '@/lib/client/@tanstack/react-query.gen'
import { useQuery } from '@tanstack/react-query'
import { usePathname } from 'next/navigation'

const ProfilePopover = () => {
  const [isOpen, setIsOpen] = useState(false)
  const pathname = usePathname()
  const { data: user } = useQuery({ ...getUserUsersMeGetOptions() })
  useEffect(() => setIsOpen(false), [pathname])

  return (
    <>
      <Popover open={isOpen} onOpenChange={setIsOpen}>
        <PopoverTrigger asChild>
          <button
            className="govuk-button govuk-!-margin-0 w-auto! !shadow-none"
            id="profile-button"
          >
            <ProfileAvatar
              size="small"
              inverse
              fullName={user?.display_name}
              aria-hidden
            />
            <span className="govuk-!-font-size-16 sr-only sm:not-sr-only">
              {user?.display_name || 'Profile'}
            </span>
            <span className="sr-only">open for profile links</span>
          </button>
        </PopoverTrigger>
        <PopoverContent
          align="end"
          aria-labelledby="display-name-heading"
          className="govuk-service-navigation--side-nav w-90 rounded-none bg-(--govuk-surface-background-colour)"
        >
          <div className="govuk-!-margin-bottom-2 flex items-center gap-4">
            <ProfileAvatar fullName={user?.display_name} />
            <div className="flex flex-col items-start">
              <h2
                className="govuk-heading-s govuk-!-margin-0"
                id="display-name-heading"
              >
                {user?.display_name}
              </h2>
              <p className="govuk-body-s govuk-!-margin-0">{user?.email}</p>
            </div>
          </div>
          <nav aria-label="Profile menu" className="flex flex-col gap-2">
            <ul>
              <li className="govuk-service-navigation__item w-full">
                <GuardedLink
                  href="/profile"
                  className="govuk-service-navigation__link"
                >
                  <User className="size-5" />
                  Your account
                </GuardedLink>
              </li>
              <li className="govuk-service-navigation__item w-full">
                <GuardedLink
                  href="/organisation-settings"
                  className="govuk-service-navigation__link"
                >
                  <Settings className="size-5" />
                  Organisation settings
                </GuardedLink>
              </li>
              <li className="govuk-service-navigation__item w-full">
                <GuardedLink
                  href="/sign-out"
                  prefetch={false}
                  className="govuk-service-navigation__link"
                >
                  <LogOut className="size-5" />
                  Sign out
                </GuardedLink>
              </li>
            </ul>
          </nav>
        </PopoverContent>
      </Popover>
    </>
  )
}

export default ProfilePopover
