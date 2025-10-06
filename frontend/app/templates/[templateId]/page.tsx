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
import { useEffect } from 'react'
import { FormProvider, useForm } from 'react-hook-form'

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

  if (!template) {
    return (
      <>
        <header className="mb-6">
          <h1 className="text-3xl font-bold">Edit template</h1>
        </header>
        <Loader2 className="animate-spin" />
      </>
    )
  }
  return (
    <>
      <header className="mb-6">
        <h1 className="text-3xl font-bold">Edit template</h1>
      </header>
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
    </>
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
      queryClient.invalidateQueries({
        queryKey: getUserTemplateUserTemplatesTemplateIdGetQueryKey({
          path: { template_id: templateId },
        }),
      })
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
