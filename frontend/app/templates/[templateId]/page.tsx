'use client'

import { DocumentTemplateEditor } from '@/app/templates/components/document-template-editor'
import { FormTemplateEditor } from '@/app/templates/components/form-template-editor'
import { TemplateNameDescriptionEditor } from '@/app/templates/components/template-name-description-editor'
import {
  deleteUserTemplateUserTemplatesTemplateIdDeleteMutation,
  editUserTemplateUserTemplatesTemplateIdPatchMutation,
  getUserTemplateUserTemplatesTemplateIdGetOptions,
  getUserTemplateUserTemplatesTemplateIdGetQueryKey,
  getUserTemplatesUserTemplatesGetQueryKey,
  getUserUsersMeGetQueryKey,
  updateDefaultTemplateUsersDefaultTemplatePatchMutation,
} from '@/lib/client/@tanstack/react-query.gen'
import { TemplateData } from '@/types/templates'
import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query'
import { Loader2, Pencil, Save, Star, StarOff } from 'lucide-react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import posthog from 'posthog-js'
import { useEffect, useState } from 'react'
import { FormProvider, useForm } from 'react-hook-form'
import { toast } from 'sonner'
import { DeleteConfirmDialog } from '../components/delete-single-template-dialog'

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
  const [isEditing, setIsEditing] = useState(false)
  const router = useRouter()
  const queryClient = useQueryClient()
  const { mutate: deleteTemplate, isPending: isDeleting } = useMutation({
    ...deleteUserTemplateUserTemplatesTemplateIdDeleteMutation(),
    onSuccess: () => {
      toast.success('Template deleted')
      queryClient.invalidateQueries({
        queryKey: getUserTemplatesUserTemplatesGetQueryKey(),
      })
      posthog.capture('template_deleted')
      router.push('/templates')
    },
  })
  const { mutate: setDefault, isPending: isSettingDefault } = useMutation({
    ...updateDefaultTemplateUsersDefaultTemplatePatchMutation(),
    onSuccess: () => {
      toast.success(
        template?.is_default
          ? 'Removed default template'
          : 'Set as default template'
      )
      queryClient.invalidateQueries({
        queryKey: getUserTemplateUserTemplatesTemplateIdGetQueryKey({
          path: { template_id: templateId },
        }),
      })
      queryClient.invalidateQueries({
        queryKey: getUserTemplatesUserTemplatesGetQueryKey(),
      })
      queryClient.invalidateQueries({
        queryKey: getUserUsersMeGetQueryKey(),
      })
    },
  })
  return (
    <div className="govuk-width-container govuk-main-wrapper">
      <nav className="govuk-breadcrumbs" aria-label="Breadcrumb">
        <ol className="govuk-breadcrumbs__list">
          <li className="govuk-breadcrumbs__list-item">
            <Link className="govuk-breadcrumbs__link" href="/templates">
              Back
            </Link>
          </li>
        </ol>
      </nav>
      {isEditing && template ? (
        <div className="govuk-grid-row govuk-!-margin-bottom-6 border-b border-(--govuk-border-colour)">
          <TemplateNameDescriptionEditor
            templateId={templateId}
            type={template.type}
            defaultValues={{
              name: template.name,
              description: template.description,
            }}
            onDone={() => setIsEditing(false)}
          />
        </div>
      ) : (
        <>
          <div className="govuk-grid-row">
            <div className="govuk-grid-column-one-half">
              <h1 className="govuk-heading-xl">{template?.name}</h1>
              <ul className="govuk-list flex gap-2">
                {template?.is_default && (
                  <li>
                    <span className="govuk-tag govuk-tag--blue govuk-!-margin-bottom-3">
                      Default
                    </span>
                  </li>
                )}
                <li>
                  <span className="govuk-tag govuk-tag--green govuk-!-margin-bottom-3">
                    {template?.type === 'document' ? 'Summary' : 'Q&A'}
                  </span>
                </li>
              </ul>
            </div>
            <div className="govuk-grid-column-one-half">
              <div className="govuk-button-group float-right">
                <button
                  className="govuk-button"
                  disabled={isSettingDefault}
                  onClick={() =>
                    setDefault({
                      body: template?.is_default
                        ? {}
                        : { template_id: templateId },
                    })
                  }
                >
                  {template?.is_default ? (
                    <>
                      <StarOff className="size-4" />
                      Remove default
                    </>
                  ) : (
                    <>
                      <Star className="size-4" />
                      Set as default
                    </>
                  )}
                </button>
                <button
                  className="govuk-button govuk-button--secondary"
                  onClick={() => setIsEditing(true)}
                >
                  <Pencil className="size-4" /> Rename
                </button>
                <DeleteConfirmDialog
                  name={template?.name ?? ''}
                  disabled={isDeleting}
                  onConfirm={() =>
                    deleteTemplate({ path: { template_id: templateId } })
                  }
                />
              </div>
            </div>
          </div>
          <div className="govuk-grid-row govuk-!-margin-bottom-6 border-b border-(--govuk-border-colour)">
            <div className="govuk-grid-column-full">
              <p className="govuk-body-l">{template?.description}</p>
            </div>
          </div>
        </>
      )}
      <div className="govuk-grid-row">
        <div className="govuk-grid-column-full">
          {template ? (
            <TemplateEditorForm
              templateId={templateId}
              defaultValues={{
                questions: template.questions,
                type: template.type,
                content: template.content,
                styleGuide: template.type === 'form' ? template.content : '',
              }}
            />
          ) : (
            <div className="flex justify-center">
              <Loader2 className="animate-spin" />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

const TemplateEditorForm = ({
  defaultValues,
  templateId,
}: {
  defaultValues: Omit<TemplateData, 'name' | 'description'>
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

  const onSubmit = (data: TemplateData) => {
    const { styleGuide, ...rest } = data
    mutate({
      path: { template_id: templateId },
      body: {
        ...rest,
        content: data.type === 'form' ? (styleGuide ?? '') : rest.content,
        questions:
          data.type === 'form' && data.questions
            ? data.questions.map((q, i) => ({ ...q, position: i }))
            : null,
      },
    })
  }

  return (
    <FormProvider {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)}>
        {defaultValues.type === 'document' && <DocumentTemplateEditor />}
        {defaultValues.type === 'form' && <FormTemplateEditor />}
        <div className="govuk-button-group">
          <button type="submit" className="govuk-button govuk-button--start">
            <Save />
            Save template
          </button>
        </div>
      </form>
    </FormProvider>
  )
}
