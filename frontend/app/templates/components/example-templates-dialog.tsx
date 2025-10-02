'use client'

import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { FileText } from 'lucide-react'

import { TemplateData } from '@/app/templates/components/editor/template-editor'
import { useState } from 'react'
import { exampleTemplates } from '../data/example-templates'

interface ExampleTemplatesDialogProps {
  onSelectTemplate: (template: TemplateData) => void
}

export function ExampleTemplatesDialog({
  onSelectTemplate,
}: ExampleTemplatesDialogProps) {
  const [open, setOpen] = useState(false)
  const handleSelectExample = (template: TemplateData) => {
    onSelectTemplate(template)
    setOpen(false)
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline">
          <FileText className="mr-2 h-4 w-4" />
          Use an example
        </Button>
      </DialogTrigger>
      <DialogContent className="max-h-[80vh] min-w-3xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Choose an example template</DialogTitle>
        </DialogHeader>
        <div className="grid grid-cols-3 gap-4">
          {exampleTemplates.map((template, index) => (
            <Card key={index} className="p-4">
              <div>
                <h3 className="mb-1 text-lg font-semibold">{template.name}</h3>
                <p className="text-sm text-gray-600">{template.description}</p>
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
  )
}
