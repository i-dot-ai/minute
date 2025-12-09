'use client'

import { DocumentTemplateEditor } from '@/app/templates/components/document-template-editor'
import { ExampleTemplatesDialog } from '@/app/templates/components/example-templates-dialog'
import { FormTemplateEditor } from '@/app/templates/components/form-template-editor'
import {
  exampleDocumentTemplates,
  exampleFormTemplates,
} from '@/app/templates/data/example-templates'
import { TemplateTypeSelect } from '@/app/templates/new/template-type-select'
import { Button } from '@/components/ui/button'
import { TemplateType } from '@/lib/client'
import { createUserTemplateUserTemplatesPostMutation } from '@/lib/client/@tanstack/react-query.gen'
import { TemplateData } from '@/types/templates'
import { useMutation } from '@tanstack/react-query'
import { ArrowRight } from 'lucide-react'
import { useRouter, useSearchParams } from 'next/navigation'
import posthog from 'posthog-js'
import { useState } from 'react'
import { FormProvider, useForm } from 'react-hook-form'
import { toast } from 'sonner'

export default function Page() {
  const [selectedType, setSelectedType] = useState<TemplateType | undefined>(
    undefined
  )
  const searchParams = useSearchParams()
  const templateTypeParam = searchParams.get('type')
  const templateExampleParam = searchParams.get('example')
  const foundExample = [
    ...exampleDocumentTemplates,
    ...exampleFormTemplates,
  ].find((v) => v.name == templateExampleParam)
  const form = useForm<TemplateData>({
    defaultValues: foundExample
      ? foundExample
      : {
          name: '',
          description: '',
          content: '',
          questions: [],
          type:
            templateTypeParam &&
            ['document', 'form'].includes(templateTypeParam)
              ? (templateTypeParam as TemplateType)
              : undefined,
        },
  })
  const navigation = useRouter()
  const { mutateAsync: saveTemplate } = useMutation({
    ...createUserTemplateUserTemplatesPostMutation(),
    onSuccess: () => {
      toast.success('Saved template!')
      posthog.capture('template_created')
      navigation.push('/templates')
    },
  })
  const onSubmit = async (data: TemplateData) => {
    await await saveTemplate({
      body: {
        ...data,
        questions:
          data.type === 'form' && data.questions
            ? data.questions.map((q, i) => ({ ...q, position: i }))
            : null,
      },
    })
  }
  const templateType = form.watch('type')
  const onSelectExample = (example: TemplateData) => {
    form.setValue('name', example.name, { shouldDirty: true })
    form.setValue('description', example.description, { shouldDirty: true })
    form.setValue('type', example.type, { shouldDirty: true })
    form.setValue('content', example.content, { shouldDirty: true })
    if (example.questions) {
      form.setValue('questions', example.questions, { shouldDirty: true })
    } else {
      form.setValue('questions', null, { shouldDirty: true })
    }
  }

  if (templateType == 'document') {
    return (
      <FormProvider {...form}>
        <header className="mb-6">
          <div className="mb-1 flex items-center gap-2">
            <h1 className="text-3xl font-bold">New template</h1>
            <ExampleTemplatesDialog
              onSelectTemplate={onSelectExample}
              examples={exampleDocumentTemplates}
            />
          </div>
          <p className="text-muted-foreground">
            Design your minute template. You can describe a structure and
            provide style guidance. Try an example to get started.
          </p>
        </header>
        <DocumentTemplateEditor onSubmit={onSubmit} />
      </FormProvider>
    )
  }

  if (templateType == 'form') {
    return (
      <FormProvider {...form}>
        <header className="mb-6">
          <div className="mb-1 flex items-center gap-2">
            <h1 className="text-3xl font-bold">New template</h1>
            <ExampleTemplatesDialog
              onSelectTemplate={onSelectExample}
              examples={exampleFormTemplates}
            />
          </div>
          <p className="text-muted-foreground">
            Design your minute template. You can describe a structure and
            provide style guidance. Try an example to get started.
          </p>
        </header>
        <FormTemplateEditor onSubmit={onSubmit} />
      </FormProvider>
    )
  }
  return (
    <div>
      <h2>Template type</h2>
      <TemplateTypeSelect value={selectedType} onChange={setSelectedType} />
      <Button
        type="button"
        onClick={() => {
          form.setValue('type', selectedType!)
        }}
        disabled={!selectedType}
      >
        Next <ArrowRight />
      </Button>
    </div>
  )
}
