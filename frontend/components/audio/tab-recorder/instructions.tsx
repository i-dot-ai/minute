import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import Image from 'next/image'
import { useEffect, useState } from 'react'

export const InstructionsTabs = () => {
  const [tab, setTab] = useState('windows')

  useEffect(() => {
    // Gross typing to make typescript happy
    const platform =
      (navigator as Navigator & { userAgentData?: { platform: string } })
        .userAgentData?.platform || navigator.platform
    setTab(platform.toLowerCase().includes('mac') ? 'macos' : 'windows')
  }, [])
  return (
    <Tabs value={tab} onValueChange={setTab}>
      <TabsList>
        <TabsTrigger value="windows" className="flex-items-center text-xs">
          <span>
            <svg className="inline size-4" viewBox="0 0 22 22">
              <g fill="#000000">
                <rect width="10" height="10" x="0" y="0" />
                <rect width="10" height="10" x="11" y="0" />
                <rect width="10" height="10" x="0" y="11" />
                <rect width="10" height="10" x="11" y="11" />
              </g>
            </svg>
          </span>
          <span>Windows</span>
        </TabsTrigger>
        <TabsTrigger value="macos" className="flex items-center text-xs">
          <span>
            <Image
              src="/apple.svg"
              width="10"
              height="10"
              className="inline w-3"
              alt="Apple logo"
            />
          </span>
          <span>MacOS</span>
        </TabsTrigger>
      </TabsList>
      <TabsContent value="windows" className="flex flex-col gap-2">
        <div className="flex items-start gap-3">
          <div className="bg-primary text-primary-foreground flex size-7 shrink-0 items-center justify-center rounded-full">
            1
          </div>
          <div>
            <p className="mb-2">
              <strong>Choose your microphone</strong> - This microphone will
              record you and those in the room with you. Note that it will
              continue recording regardless of whether you are muted in the
              virutal meeting.
            </p>
          </div>
        </div>
        <div className="flex items-start gap-3">
          <div className="bg-primary text-primary-foreground flex size-7 shrink-0 items-center justify-center rounded-full">
            2
          </div>
          <div>
            <p className="mb-2">
              <strong>Join your meeting</strong> - Join your meeting in Teams,
              Google Meet, Zoom.
            </p>
          </div>
        </div>
        <div className="flex items-start gap-3">
          <div className="bg-primary text-primary-foreground flex size-7 shrink-0 items-center justify-center rounded-full">
            3
          </div>
          <div>
            <p className="mb-2">
              <strong>Share your screen</strong> - When prompted, click the
              &quot;
              <strong>Entire Screen</strong>&quot; tab and select the screen
              where the meeting is showing.
            </p>
          </div>
        </div>
        <div className="flex items-start gap-3">
          <div className="bg-primary text-primary-foreground flex size-7 shrink-0 items-center justify-center rounded-full">
            4
          </div>
          <p>
            <strong>Select &quot;Share Audio&quot;</strong>. Switch on the
            &quot;Share Audio&quot; the toggle in the bottom right of the share
            window.
          </p>
        </div>
        <div className="flex items-start gap-3">
          <div className="bg-primary text-primary-foreground flex size-7 shrink-0 items-center justify-center rounded-full">
            5
          </div>
          <p>
            <strong>Keep Minute open</strong> - It doesn&apos;t need to be
            visible on screen, but do not close Minute&apos;s tab
          </p>
        </div>
      </TabsContent>
      <TabsContent value="macos" className="flex flex-col gap-2">
        <div className="flex items-start gap-3">
          <div className="bg-primary text-primary-foreground flex size-7 shrink-0 items-center justify-center rounded-full">
            1
          </div>
          <div>
            <p className="mb-2">
              <strong>Choose your microphone</strong> - This microphone will
              record you and those in the room with you. Note that it will
              continue recording regardless of whether you are muted in the
              virutal meeting.
            </p>
          </div>
        </div>
        <div className="flex items-start gap-3">
          <div className="bg-primary text-primary-foreground flex size-7 shrink-0 items-center justify-center rounded-full">
            2
          </div>
          <div>
            <p className="mb-2">
              <strong>Join your meeting</strong> - Join your meeting in a
              browser tab. It must be the same browser that Minute is running
              in. Do not use a desktop app. Desktop apps cannot be recorded.
            </p>
          </div>
        </div>
        <div className="flex items-start gap-3">
          <div className="bg-primary text-primary-foreground flex size-7 shrink-0 items-center justify-center rounded-full">
            3
          </div>
          <div>
            <p className="mb-2">
              <strong>Share the right tab</strong> - When prompted, select the
              tab where you have joined the meeting.
            </p>
          </div>
        </div>
        <div className="flex items-start gap-3">
          <div className="bg-primary text-primary-foreground flex size-7 shrink-0 items-center justify-center rounded-full">
            4
          </div>
          <p>
            <strong>Select &quot;Share Audio&quot;</strong>. Switch on the
            &quot;Share Audio&quot; the toggle in the bottom right of the share
            window.
          </p>
        </div>
        <div className="flex items-start gap-3">
          <div className="bg-primary text-primary-foreground flex size-7 shrink-0 items-center justify-center rounded-full">
            5
          </div>
          <p>
            <strong>Keep both tabs open</strong> - Don&apos;t close either tab
            during recording. Switching between tabs is fine, but both must
            remain open.
          </p>
        </div>
      </TabsContent>
    </Tabs>
  )
}
