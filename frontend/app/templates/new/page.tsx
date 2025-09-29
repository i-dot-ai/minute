'use client'

import {
  TemplateData,
  TemplateEditor,
} from '@/app/templates/components/editor/template-editor'
import { ExampleTemplatesDialog } from '@/app/templates/components/example-templates-dialog'
import { createUserTemplateUserTemplatesPostMutation } from '@/lib/client/@tanstack/react-query.gen'
import { useMutation } from '@tanstack/react-query'
import { useRouter } from 'next/navigation'
import { useState } from 'react'

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

  const handleSelectExample = (template: TemplateData) => {
    setSelectedTemplate(template)
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-3xl font-bold">New template</h1>
        <ExampleTemplatesDialog onSelectTemplate={handleSelectExample} />
      </div>
      <TemplateEditor
        defaultValues={selectedTemplate || undefined}
        onSubmit={(body) => {
          saveTemplate({ body })
        }}
      />
    </div>
  )
}
