'use client'

import { DocumentTemplateEditor } from '@/app/templates/components/document-template-editor'
import { FormTemplateEditor } from '@/app/templates/components/form-template-editor'
import {
  exampleDocumentTemplates,
  exampleFormTemplates,
} from '@/app/templates/data/example-templates'
import { TemplateType } from '@/lib/client'
import { createUserTemplateUserTemplatesPostMutation } from '@/lib/client/@tanstack/react-query.gen'
import { TemplateData } from '@/types/templates'
import { useMutation } from '@tanstack/react-query'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import posthog from 'posthog-js'
import { Suspense } from 'react'
import { FormProvider, useForm } from 'react-hook-form'
import { toast } from 'sonner'

function NewTemplateContent() {
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
    await saveTemplate({
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

  return (
    <FormProvider {...form}>
      <div className="govuk-width-container govuk-main-wrapper">
        <nav className="govuk-breadcrumbs" aria-label="Breadcrumb">
          <ol className="govuk-breadcrumbs__list">
            <li className="govuk-breadcrumbs__list-item">
              <Link className="govuk-breadcrumbs__link" href="/">
                Home
              </Link>
            </li>
            <li className="govuk-breadcrumbs__list-item">
              <Link className="govuk-breadcrumbs__link" href="/templates">
                Templates
              </Link>
            </li>
          </ol>
        </nav>
        <div className="govuk-grid-row">
          <div className="govuk-grid-column-two-thirds">
            <h1 className="govuk-heading-xl">New {templateType} template</h1>
            <p className="govuk-body">
              Design your minute template. You can describe a structure and
              provide style guidance. Try an example to get started.
            </p>
            {templateType === 'document' ? (
              <DocumentTemplateEditor onSubmit={onSubmit} />
            ) : (
              <FormTemplateEditor onSubmit={onSubmit} />
            )}
          </div>
        </div>
      </div>
    </FormProvider>
  )
}

export default function Page() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <NewTemplateContent />
    </Suspense>
  )
}
