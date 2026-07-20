'use client'

import { DocumentTemplateEditor } from '@/app/templates/components/document-template-editor'
import { FormTemplateEditor } from '@/app/templates/components/form-template-editor'
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
import { Loader2, Pencil, Star, StarOff } from 'lucide-react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import posthog from 'posthog-js'
import { useCallback, useState } from 'react'
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

  const form = useForm<TemplateData>()
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = form

  const resetToTemplate = useCallback(() => {
    if (!template) return
    reset({
      name: template.name,
      description: template.description,
      type: template.type,
      content: template.content,
      styleGuide: template.type === 'form' ? template.content : '',
      questions: template.questions,
    })
  }, [reset, template])

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
  const { mutate: saveTemplate, isPending: isSaving } = useMutation({
    ...editUserTemplateUserTemplatesTemplateIdPatchMutation(),
    onSuccess: () => {
      toast.success('Changes saved!', { position: 'top-center' })
      queryClient.invalidateQueries({
        queryKey: getUserTemplateUserTemplatesTemplateIdGetQueryKey({
          path: { template_id: templateId },
        }),
      })
      queryClient.invalidateQueries({
        queryKey: getUserTemplatesUserTemplatesGetQueryKey(),
      })
      posthog.capture('template_edited')
      setIsEditing(false)
    },
  })

  const handleSave = handleSubmit((data) => {
    const { styleGuide, ...rest } = data
    saveTemplate({
      path: { template_id: templateId },
      body: {
        name: rest.name,
        description: rest.description,
        content: data.type === 'form' ? (styleGuide ?? '') : rest.content,
        questions:
          data.type === 'form' && data.questions
            ? data.questions.map((q, i) => ({ ...q, position: i }))
            : null,
      },
    })
  })

  const handleDiscard = () => {
    resetToTemplate()
    setIsEditing(false)
  }

  return (
    <div>
      <div className="govuk-!-padding-top-4 govuk-!-padding-bottom-4 sticky top-0 z-10 bg-white">
        <div className="govuk-width-container">
          <div className="govuk-grid-row">
            <div className="govuk-grid-column-one-third">
              <nav
                className="govuk-breadcrumbs govuk-!-margin-bottom-0"
                aria-label="Breadcrumb"
              >
                <ol className="govuk-breadcrumbs__list">
                  <li className="govuk-breadcrumbs__list-item">
                    <Link className="govuk-breadcrumbs__link" href="/templates">
                      Back
                    </Link>
                  </li>
                </ol>
              </nav>
            </div>
            <div className="govuk-grid-column-two-thirds">
              {!isEditing && (
                <div className="govuk-button-group govuk-!-margin-bottom-0 justify-end">
                  <button
                    className="govuk-button govuk-button--secondary govuk-!-margin-bottom-0"
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
                    className="govuk-button govuk-button--secondary govuk-!-margin-bottom-0"
                    onClick={() => {
                      resetToTemplate()
                      setIsEditing(true)
                    }}
                  >
                    <Pencil className="size-4" /> Edit
                  </button>
                  <DeleteConfirmDialog
                    name={template?.name ?? ''}
                    disabled={isDeleting}
                    onConfirm={() =>
                      deleteTemplate({ path: { template_id: templateId } })
                    }
                  />
                </div>
              )}
              {isEditing && (
                <div className="govuk-button-group govuk-!-margin-bottom-0 justify-end">
                  <button
                    type="button"
                    className="govuk-button govuk-button--secondary govuk-!-margin-bottom-0"
                    onClick={handleDiscard}
                  >
                    Discard
                  </button>
                  <button
                    type="button"
                    className="govuk-button govuk-!-margin-bottom-0"
                    onClick={handleSave}
                    disabled={isSaving}
                  >
                    Save
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
      <div className="govuk-width-container">
        <div className="govuk-grid-row">
          <div className="govuk-grid-column-full">
            {template && isEditing && (
              <FormProvider {...form}>
                <div className="govuk-!-padding-4 bg-(--govuk-surface-background-colour)">
                  <form onSubmit={handleSave}>
                    <div className="text-red-600">
                      <p className="govuk-body">{errors.name?.message ?? null}</p>
                      <p className="govuk-body">
                        {errors.description?.message ?? null}
                      </p>
                    </div>
                    <div className="govuk-form-group">
                      <h1 className="govuk-label-wrapper">
                        <label
                          className="govuk-label govuk-label--s"
                          htmlFor="name"
                        >
                          Template name
                        </label>
                      </h1>
                      <input
                        id="name"
                        className="govuk-input govuk-!-width-one-half bg-white"
                        {...register('name', {
                          required: {
                            value: true,
                            message: 'Template name required',
                          },
                        })}
                      />
                    </div>
                    <div className="govuk-form-group">
                      <label
                        className="govuk-label govuk-label--s"
                        htmlFor="description"
                      >
                        Description
                      </label>
                      <textarea
                        id="description"
                        className="govuk-textarea govuk-!-width-one-half bg-white"
                        rows={3}
                        {...register('description', {
                          required: {
                            value: true,
                            message: 'Description required',
                          },
                        })}
                      />
                    </div>
                    {template.type === 'document' && <DocumentTemplateEditor />}
                    {template.type === 'form' && <FormTemplateEditor />}
                  </form>
                </div>
              </FormProvider>
            )}
            {template && !isEditing && (
              <>
                <h1 className="govuk-heading-l govuk-!-margin-top-4">
                  {template.name}
                </h1>
                <ul className="govuk-list govuk-!-margin-bottom-4 flex gap-2">
                  <li>
                    <span className="govuk-tag govuk-tag--green">
                      {template.type === 'document' ? 'Summary' : 'Q&A'}
                    </span>
                  </li>
                  {template.is_default && (
                    <li>
                      <span className="govuk-tag govuk-tag--blue">Default</span>
                    </li>
                  )}
                </ul>
                <p className="govuk-body-l">{template.description}</p>
                {template.type === 'document' ? (
                  <>
                    <h2 className="govuk-heading-s">Template content</h2>
                    <div
                      className="editor-content"
                      dangerouslySetInnerHTML={{ __html: template.content }}
                    />
                  </>
                ) : (
                  <>
                    <h2 className="govuk-heading-m">Style guide</h2>
                    <div
                      className="govuk-!-margin-bottom-4"
                      dangerouslySetInnerHTML={{ __html: template.content }}
                    />
                    <h2 className="govuk-heading-m">Questions</h2>
                    <ol className="govuk-list govuk-list--number">
                      {template.questions?.map((question) => (
                        <li key={question.id}>
                          <div className="">
                            <h3 className="govuk-heading-s">
                              {question.title}
                            </h3>
                            <p className="govuk-body">{question.description}</p>
                          </div>
                        </li>
                      ))}
                    </ol>
                  </>
                )}
              </>
            )}
            {!template && (
              <div className="flex justify-center">
                <Loader2 className="animate-spin" />
              </div>
            )}
          </div>
        </div>
      </div>
    </div >
  )
}
