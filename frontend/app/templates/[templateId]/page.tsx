'use client'

import { DocumentTemplateEditor } from '@/app/templates/components/document-template-editor'
import { FormTemplateEditor } from '@/app/templates/components/form-template-editor'
import {
  editUserTemplateUserTemplatesTemplateIdPatchMutation,
  getUserTemplateUserTemplatesTemplateIdGetOptions,
  getUserTemplateUserTemplatesTemplateIdGetQueryKey,
} from '@/lib/client/@tanstack/react-query.gen'
import { TemplateData } from '@/types/templates'
import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query'
import { Loader2 } from 'lucide-react'
import Link from 'next/link'
import posthog from 'posthog-js'
import { useEffect } from 'react'
import { FormProvider, useForm } from 'react-hook-form'
import { toast } from 'sonner'

export default function EditTemplatePage({
  params: { templateId },
}: {
  params: { templateId: string }
}) {
  const { data: template } = useQuery({
    ...getUserTemplateUserTemplatesTemplateIdGetOptions({
      path: { template_id: templateId },
    }),
    placeholderData: keepPreviousData,
  })
  return (
    <div className="govuk-width-container govuk-main-wrapper">
      <nav className="govuk-breadcrumbs" aria-label="Breadcrumb">
        <ol className="govuk-breadcrumbs__list">
          <li className="govuk-breadcrumbs__list-item">
            <Link className="govuk-breadcrumbs__link" href="/">Home</Link>
          </li>
          <li className="govuk-breadcrumbs__list-item">
            <Link className="govuk-breadcrumbs__link" href="/templates">Templates</Link>
          </li>
        </ol>
      </nav>
      <div className="govuk-grid-row">
        <div className="govuk-grid-column-two-thirds">
          <h1 className="govuk-heading-xl">Edit template</h1>
          {
            template ? (
              <TemplateEditorForm
                templateId={templateId}
                defaultValues={{
                  name: template.name,
                  description: template.description,
                  questions: template.questions,
                  type: template.type,
                  content: template.content,
                }}
              />
            ) : (
              <div className="flex justify-center">
                <Loader2 className="animate-spin" />
              </div>
            )
          }
        </div>
      </div>
    </div>
  )
}

const TemplateEditorForm = ({
  defaultValues,
  templateId,
}: {
  defaultValues: TemplateData
  templateId: string
}) => {
  const form = useForm<TemplateData>({ defaultValues })

  useEffect(() => {
    if (form.formState.isSubmitSuccessful) {
      form.reset(form.getValues(), { keepValues: true })
    }
  }, [form, form.formState.isSubmitSuccessful])

  const queryClient = useQueryClient()
  const { mutate } = useMutation({
    ...editUserTemplateUserTemplatesTemplateIdPatchMutation(),
    onSuccess: () => {
      toast.success('Changes saved!', { position: 'top-center' })
      queryClient.invalidateQueries({
        queryKey: getUserTemplateUserTemplatesTemplateIdGetQueryKey({
          path: { template_id: templateId },
        }),
      })
      posthog.capture('template_edited')
    },
  })
  if (defaultValues.type === 'document') {
    return (
      <FormProvider {...form}>
        <DocumentTemplateEditor
          onSubmit={(data) =>
            mutate({
              path: { template_id: templateId },
              body: { ...data, questions: null },
            })
          }
        />
      </FormProvider>
    )
  }
  if (defaultValues.type === 'form') {
    return (
      <FormProvider {...form}>
        <FormTemplateEditor
          onSubmit={(data) =>
            mutate({
              path: { template_id: templateId },
              body: {
                ...data,
                questions:
                  data.questions?.map((q, i) => ({
                    ...q,
                    position: i,
                  })) || null,
              },
            })
          }
        />
      </FormProvider>
    )
  }
}
