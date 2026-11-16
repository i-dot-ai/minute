'use client'

import { LogOut, Phone } from 'lucide-react'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { useEffect, useState } from 'react'
import { GuardedLink } from '@/components/navigation/guarded-link'
import ProfileAvatar from '@/components/profile-avatar'
import { ChangeNameDialog } from '@/components/header/change-name-dialog'
import { getUserUsersMeGetOptions } from '@/lib/client/@tanstack/react-query.gen'
import { useQuery } from '@tanstack/react-query'
import { usePathname } from 'next/navigation'

const ProfilePopover = () => {
  const [isOpen, setIsOpen] = useState(false)
  const [nameDialogOpen, setNameDialogOpen] = useState(false)
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
            role="button"
          >
            <ProfileAvatar size="small" fullName={user?.display_name} />
            <span className="govuk-!-font-size-16 hidden sm:inline">
              {user?.display_name || 'Profile'}
            </span>
          </button>
        </PopoverTrigger>
        <PopoverContent
          align="end"
          aria-labelledby="display-name-heading"
          className="govuk-service-navigation--side-nav w-90 rounded-none bg-(--govuk-surface-background-colour)"
        >
          {user?.roles && user.roles.length > 0 && (
            <ul className="govuk-list govuk-!-margin-bottom-0 flex justify-end gap-2">
              {user.roles.map((role) => (
                <li key={role}>
                  <span
                    className={`govuk-tag${role === 'admin' ? 'govuk-tag--grey' : ''}`}
                  >
                    {role}
                  </span>
                </li>
              ))}
            </ul>
          )}
          <div className="flex items-center gap-4">
            <ProfileAvatar fullName={user?.display_name} />
            <div className="flex flex-col items-start">
              <h2
                className="govuk-heading-s govuk-!-margin-0"
                id="display-name-heading"
              >
                {user?.display_name}
              </h2>
              <p className="govuk-body-s govuk-!-margin-0">{user?.email}</p>

              <button
                type="button"
                className="govuk-link govuk-link--no-visited-state govuk-link--no-underline cursor-pointer text-(--govuk-link-colour)"
                onClick={() => {
                  setIsOpen(false)
                  setNameDialogOpen(true)
                }}
              >
                Change name
              </button>
            </div>
          </div>
          <nav
            aria-label="Profile menu"
            className="hidden flex-col gap-2 sm:flex"
          >
            <ul>
              <li className="govuk-service-navigation__item w-full">
                <GuardedLink
                  href="/support"
                  className="govuk-service-navigation__link"
                >
                  <Phone className="size-5" />
                  Contact us
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
            <ul className="flex justify-center gap-4">
              <li>
                <GuardedLink
                  href="/privacy"
                  className="govuk-link govuk-link--no-visited-state govuk-link--no-underline !text-[#484949]"
                >
                  Privacy
                </GuardedLink>
              </li>
              <li>
                <GuardedLink
                  href="/accessibility"
                  className="govuk-link govuk-link--no-visited-state govuk-link--no-underline !text-[#484949]"
                >
                  Accessibility
                </GuardedLink>
              </li>
            </ul>
          </nav>
        </PopoverContent>
      </Popover>
      <ChangeNameDialog
        open={nameDialogOpen}
        onOpenChange={setNameDialogOpen}
        displayName={user?.display_name}
      />
    </>
  )
}

export default ProfilePopover
