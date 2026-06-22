'use client'

import { ExampleTemplatesDialog } from '@/app/templates/components/example-templates-dialog'
import {
  exampleDocumentTemplates,
  exampleFormTemplates,
} from '@/app/templates/data/example-templates'
import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'

import { TemplateResponse } from '@/lib/client'
import {
  deleteUserTemplateUserTemplatesTemplateIdDeleteMutation,
  duplicateUserTemplateUserTemplatesTemplateIdDuplicatePostMutation,
  getUserTemplatesUserTemplatesGetOptions,
  getUserTemplatesUserTemplatesGetQueryKey,
} from '@/lib/client/@tanstack/react-query.gen'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CopyPlus, FileWarning, Loader2, Plus } from 'lucide-react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import posthog from 'posthog-js'
import { useMemo } from 'react'

export const UserTemplatesList = () => {
  const {
    data: templates = [],
    isLoading,
    isError,
  } = useQuery(getUserTemplatesUserTemplatesGetOptions())
  const [documentTemplates, formTemplates] = useMemo(() => {
    const docs = []
    const forms = []
    for (const template of templates) {
      if (template.type == 'document') {
        docs.push(template)
      } else {
        forms.push(template)
      }
    }
    return [docs, forms]
  }, [templates])
  const router = useRouter()
  if (isLoading) {
    return <Loader2 className="animate-spin" />
  }
  if (isError) {
    return (
      <div>
        <FileWarning />
        <p className="govuk-body">
          Something went wrong fetching your templates
        </p>
      </div>
    )
  }

  return (
    <>
      <div data-onboarding="document-templates">
        <h2
          className="govuk-heading-l govuk-!-margin-bottom-2"
          id="document-templates"
        >
          Document templates
        </h2>
        <p className="govuk-body">
          Customise the structure and style of your minutes.
        </p>
        <div className="govuk-button-group">
          <Link
            className="govuk-button"
            role="button"
            href="/templates/new?type=document"
          >
            <Plus className="size-4" /> Create a new document template
          </Link>
          <ExampleTemplatesDialog
            onSelectTemplate={(example) => {
              router.push(`/templates/new?example=${example.name}`)
            }}
            examples={exampleDocumentTemplates}
          />
        </div>
        {documentTemplates.length > 0 && (
          <>
            <h3 className="govuk-heading-m govuk-!-margin-bottom-2">
              Your document templates
            </h3>
            <ul className="govuk-list">
              {documentTemplates.map((template) => (
                <TemplateListItem template={template} key={template.id} />
              ))}
            </ul>
          </>
        )}
      </div>
      <div data-onboarding="form-templates">
        <h2
          className="govuk-heading-l govuk-!-margin-bottom-2"
          id="form-templates"
        >
          Form templates
        </h2>
        <p className="govuk-body">
          For complex summarisation of meetings into many questions and answers.
        </p>
        <div className="govuk-button-group">
          <Link
            href="/templates/new?type=form"
            className="govuk-button"
            role="button"
          >
            <Plus className="size-4" /> Create a new form template
          </Link>
          <ExampleTemplatesDialog
            onSelectTemplate={(example) => {
              router.push(`/templates/new?example=${example.name}`)
            }}
            examples={exampleFormTemplates}
          />
        </div>
        {formTemplates.length > 0 && (
          <>
            <h3 className="govuk-heading-m govuk-!-margin-bottom-2">
              Your form templates
            </h3>
            <ul className="govuk-list">
              {formTemplates.map((template) => (
                <TemplateListItem template={template} key={template.id} />
              ))}
            </ul>
          </>
        )}
      </div>
    </>
  )
}
const TemplateListItem = ({ template }: { template: TemplateResponse }) => {
  const queryClient = useQueryClient()
  const deleteMutation = useMutation({
    ...deleteUserTemplateUserTemplatesTemplateIdDeleteMutation(),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: getUserTemplatesUserTemplatesGetQueryKey(),
      })
      posthog.capture('template_deleted')
    },
  })
  const duplicationMutation = useMutation({
    ...duplicateUserTemplateUserTemplatesTemplateIdDuplicatePostMutation(),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: getUserTemplatesUserTemplatesGetQueryKey(),
      })
      posthog.capture('template_duplicated')
    },
  })
  return (
    <li
      key={template.id}
      className="transcriptions__list-item govuk-!-padding-top-3 govuk-!-padding-bottom-3 flex items-start justify-between"
    >
      <div>
        <h4 className="govuk-heading-s govuk-!-margin-bottom-1">
          <Link className="govuk-link" href={`/templates/${template.id}`}>
            {template.name}
          </Link>
        </h4>
        <p className="govuk-body govuk-!-margin-bottom-1">
          {template.description}
        </p>
        <p className="govuk-body-s">
          Updated {new Date(template.updated_datetime!).toLocaleDateString()}
        </p>
      </div>
      <div className="govuk-button-group">
        <button
          onClick={() => {
            duplicationMutation.mutate({
              path: { template_id: template.id },
            })
          }}
          className="govuk-button govuk-button--secondary"
        >
          <CopyPlus className="size-4" /> Duplicate
        </button>
        <DeleteConfirmDialog
          template={template}
          onConfirm={() => {
            deleteMutation.mutate({
              path: { template_id: template.id! },
            })
          }}
        />
      </div>
    </li>
  )
}

const DeleteConfirmDialog = ({
  template,
  onConfirm,
}: {
  template: TemplateResponse
  onConfirm: () => void
}) => (
  <AlertDialog>
    <AlertDialogTrigger asChild>
      <button className="govuk-link link--warning">Delete</button>
    </AlertDialogTrigger>
    <AlertDialogContent>
      <h1 className="govuk-heading-l">Delete Template</h1>
      <p className="govuk-body">
        Are you sure you want to delete <strong>{template.name}</strong>? This
        action cannot be undone.
      </p>
      <div className="govuk-button-group">
        <button
          className="govuk-button govuk-button--warning"
          onClick={onConfirm}
        >
          Delete
        </button>
        <button className="govuk-button govuk-button--secondary">Cancel</button>
      </div>
    </AlertDialogContent>
  </AlertDialog>
)
