import { Alpha } from '@/components/layout/alpha'
import { NavButton } from '@/components/layout/nav-button'
import { FeatureFlags } from '@/lib/feature-flags'
import { getServerSideFeatureFlag } from '@/lib/posthog'
import { FileText, Home, Settings } from 'lucide-react'
import Link from 'next/link'

export const Header = async () => {
  const userTemplatesEnabled = await getServerSideFeatureFlag(
    FeatureFlags.UserTemplatesEnabled
  )
  return (
    <>
      <header className="flex h-[64px] items-center justify-between border-b border-gray-200 bg-black px-8 dark:border-gray-800">
        <div className="flex items-center">
          <Link
            href="/"
            target="_blank"
            className="font-gds-transport flex items-center gap-3 text-3xl text-white"
          >
            <svg
              width="32"
              height="32"
              viewBox="0 0 32 32"
              fill="white"
              focusable="false"
              aria-hidden="true"
            >
              <path d="M22.6 10.4c-1 .4-2-.1-2.4-1-.4-.9.1-2 1-2.4.9-.4 2 .1 2.4 1s-.1 2-1 2.4m-5.9 6.7c-.9.4-2-.1-2.4-1-.4-.9.1-2 1-2.4.9-.4 2 .1 2.4 1s-.1 2-1 2.4m10.8-3.7c-1 .4-2-.1-2.4-1-.4-.9.1-2 1-2.4.9-.4 2 .1 2.4 1s0 2-1 2.4m3.3 4.8c-1 .4-2-.1-2.4-1-.4-.9.1-2 1-2.4.9-.4 2 .1 2.4 1s-.1 2-1 2.4M17 4.7l2.3 1.2V2.5l-2.3.7-.2-.2.9-3h-3.4l.9 3-.2.2c-.1.1-2.3-.7-2.3-.7v3.4L15 4.7c.1.1.1.2.2.2l-1.3 4c-.1.2-.1.4-.1.6 0 1.1.8 2 1.9 2.2h.7c1-.2 1.9-1.1 1.9-2.1 0-.2 0-.4-.1-.6l-1.3-4c-.1-.2 0-.2.1-.3m-7.6 5.7c.9.4 2-.1 2.4-1 .4-.9-.1-2-1-2.4-.9-.4-2 .1-2.4 1s0 2 1 2.4m-5 3c.9.4 2-.1 2.4-1 .4-.9-.1-2-1-2.4-.9-.4-2 .1-2.4 1s.1 2 1 2.4m-3.2 4.8c.9.4 2-.1 2.4-1 .4-.9-.1-2-1-2.4-.9-.4-2 .1-2.4 1s0 2 1 2.4m14.8 11c4.4 0 8.6.3 12.3.8 1.1-4.5 2.4-7 3.7-8.8l-2.5-.9c.2 1.3.3 1.9 0 2.7-.4-.4-.8-1.1-1.1-2.3l-1.2 4c.7-.5 1.3-.8 2-.9-1.1 2.5-2.6 3.1-3.5 3-1.1-.2-1.7-1.2-1.5-2.1.3-1.2 1.5-1.5 2.1-.1 1.1-2.3-.8-3-2-2.3 1.9-1.9 2.1-3.5.6-5.6-2.1 1.6-2.1 3.2-1.2 5.5-1.2-1.4-3.2-.6-2.5 1.6.9-1.4 2.1-.5 1.9.8-.2 1.1-1.7 2.1-3.5 1.9-2.7-.2-2.9-2.1-2.9-3.6.7-.1 1.9.5 2.9 1.9l.4-4.3c-1.1 1.1-2.1 1.4-3.2 1.4.4-1.2 2.1-3 2.1-3h-5.4s1.7 1.9 2.1 3c-1.1 0-2.1-.2-3.2-1.4l.4 4.3c1-1.4 2.2-2 2.9-1.9-.1 1.5-.2 3.4-2.9 3.6-1.9.2-3.4-.8-3.5-1.9-.2-1.3 1-2.2 1.9-.8.7-2.3-1.2-3-2.5-1.6.9-2.2.9-3.9-1.2-5.5-1.5 2-1.3 3.7.6 5.6-1.2-.7-3.1 0-2 2.3.6-1.4 1.8-1.1 2.1.1.2.9-.3 1.9-1.5 2.1-.9.2-2.4-.5-3.5-3 .6 0 1.2.3 2 .9l-1.2-4c-.3 1.1-.7 1.9-1.1 2.3-.3-.8-.2-1.4 0-2.7l-2.9.9C1.3 23 2.6 25.5 3.7 30c3.7-.5 7.9-.8 12.3-.8" />
            </svg>
            <span className="font-gds-transport text-3xl text-white">
              Minute
            </span>
          </Link>
        </div>
        <div>
          <Link
            href="https://ai.gov.uk"
            target="_blank"
            rel="noopener noreferrer"
          >
            <svg
              width="65"
              height="40"
              aria-label="i.AI"
              focusable="false"
              viewBox="0 0 167 105"
            >
              <g id="Layer_2" data-name="Layer 2">
                <g id="Layer_1-2" data-name="Layer 1">
                  <rect y="24.937" width="22" fill="#fff" height="80" x="0" />
                  <rect
                    fill="#c50878"
                    x="144.87"
                    width="21.82"
                    height="104.15"
                  />
                  <circle r="11" cx="11" fill="#fff" cy="11" />
                  <path
                    fill="#c50878"
                    d="M122.1,104.15,115,83.7H79.41l-6.75,20.45H48.52L87.06,0H108.6l38.15,104.15ZM97.44,27.8,85.76,63.55h23.1Z"
                  />
                  <circle r="11" cx="36.700001" fill="#fff" cy="93.682587" />
                </g>
              </g>
            </svg>
          </Link>
        </div>
      </header>

      <div className="header-grid w-full items-center border-b px-6 py-1">
        <div
          className="flex items-center justify-center"
          style={{ gridArea: 'alpha' }}
        >
          <Alpha />
        </div>
        <div className="flex items-center" style={{ gridArea: 'nav' }}>
          <NavButton href="/">
            <Home size="1rem" /> Home
          </NavButton>
          {userTemplatesEnabled && (
            <NavButton href="/templates">
              <FileText size="1rem" /> Templates
            </NavButton>
          )}
          <NavButton href="/settings">
            <Settings size="1rem" /> Settings
          </NavButton>
        </div>
      </div>
    </>
  )
}
