import React from 'react'
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'

export default function SupportPage() {
  return (
    <div className="container max-w-4xl py-6 md:py-10">
      <div className="space-y-6">
        <h1 className="text-4xl font-bold tracking-tight">Support Center</h1>

        <div className="grid gap-4 md:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Need Help?</CardTitle>
              <CardDescription>Contact our support team</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-muted-foreground">
                Email us at:{' '}
                <a href="mailto:minute-support@cabinetoffice.gov.uk">
                  minute-support@cabinetoffice.gov.uk
                </a>
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Response Time</CardTitle>
              <CardDescription>What to expect</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-muted-foreground">
                We aim to respond to all inquiries within 24 hours.
              </p>
            </CardContent>
          </Card>
        </div>

        <Accordion type="single" collapsible className="w-full">
          <AccordionItem value="faq-1">
            <AccordionTrigger>
              How do I start a new transcription?
            </AccordionTrigger>
            <AccordionContent>
              Upload your audio/video file or start a new recording directly
              from your browser.
            </AccordionContent>
          </AccordionItem>
          <AccordionItem value="faq-2">
            <AccordionTrigger>
              What file formats are supported?
            </AccordionTrigger>
            <AccordionContent>
              We support most common audio and video formats including MP3, WAV,
              MP4, and M4A.
            </AccordionContent>
          </AccordionItem>
        </Accordion>
      </div>
    </div>
  )
}
