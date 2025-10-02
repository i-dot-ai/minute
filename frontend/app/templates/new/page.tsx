'use client'

import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { FileText } from 'lucide-react'

import {
  TemplateData,
  TemplateEditor,
} from '@/app/templates/components/editor/template-editor'
import { createUserTemplateUserTemplatesPostMutation } from '@/lib/client/@tanstack/react-query.gen'
import { useMutation } from '@tanstack/react-query'
import { useRouter } from 'next/navigation'
import { useState } from 'react'
import { exampleTemplates } from '../data/example-templates'

export default function NewTemplatePage() {
  const navigation = useRouter()
  const [selectedTemplate, setSelectedTemplate] = useState<TemplateData | null>(
    null
  )

  const { mutate: saveTemplate } = useMutation({
    ...createUserTemplateUserTemplatesPostMutation(),
    onSuccess: () => {
      navigation.push('/templates')
    },
  })
  const [open, setOpen] = useState(false)
  const handleSelectExample = (template: TemplateData) => {
    setSelectedTemplate(template)
    setOpen(false)
  }

  return (
    <>
      <div>
        <header className="mb-6">
          <div className="mb-1 flex items-center gap-2">
            <h1 className="text-3xl font-bold">New template</h1>
            <Button variant="outline" onClick={() => setOpen(true)}>
              <FileText className="mr-2 h-4 w-4" />
              Use an example
            </Button>
          </div>
          <p className="text-muted-foreground">
            Design your minute template. You can describe a structure and
            provide style guidance or{' '}
            <span
              className="underline hover:cursor-pointer hover:decoration-2"
              onClick={() => setOpen(true)}
            >
              try an example
            </span>{' '}
            to get started.
          </p>
        </header>
        <TemplateEditor
          defaultValues={selectedTemplate || undefined}
          onSubmit={(body) => {
            saveTemplate({ body })
          }}
        />
      </div>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-h-[80vh] min-w-3xl overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Choose an example template</DialogTitle>
          </DialogHeader>
          <div className="grid grid-cols-3 gap-4">
            {exampleTemplates.map((template, index) => (
              <Card key={index} className="p-4">
                <div>
                  <h3 className="mb-1 text-lg font-semibold">
                    {template.name}
                  </h3>
                  <p className="text-sm text-gray-600">
                    {template.description}
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleSelectExample(template)}
                    className="flex items-center gap-1"
                  >
                    Use this template
                  </Button>
                </div>
              </Card>
            ))}
          </div>
        </DialogContent>
      </Dialog>
    </>
  )
}
