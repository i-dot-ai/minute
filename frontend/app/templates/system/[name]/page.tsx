'use client'

import {
  getTemplatesTemplatesGetOptions,
  getTemplatesTemplatesGetQueryKey,
  getUserTemplatesUserTemplatesGetQueryKey,
  getUserUsersMeGetQueryKey,
  updateDefaultTemplateUsersDefaultTemplatePatchMutation,
} from '@/lib/client/@tanstack/react-query.gen'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Loader2, Star, StarOff } from 'lucide-react'
import Link from 'next/link'
import { notFound } from 'next/navigation'
import { toast } from 'sonner'

export default function SystemTemplatePage({
  params: { name },
}: {
  params: { name: string }
}) {
  const templateName = decodeURIComponent(name)
  const { data: templates, isLoading } = useQuery(
    getTemplatesTemplatesGetOptions()
  )
  const queryClient = useQueryClient()

  const template = templates?.find((t) => t.name === templateName)

  const { mutate: setDefault, isPending: isSettingDefault } = useMutation({
    ...updateDefaultTemplateUsersDefaultTemplatePatchMutation(),
    onSuccess: () => {
      toast.success(
        template?.is_default
          ? 'Removed default template'
          : 'Set as default template'
      )
      queryClient.invalidateQueries({
        queryKey: getTemplatesTemplatesGetQueryKey(),
      })
      queryClient.invalidateQueries({
        queryKey: getUserTemplatesUserTemplatesGetQueryKey(),
      })
      queryClient.invalidateQueries({
        queryKey: getUserUsersMeGetQueryKey(),
      })
    },
  })

  if (isLoading) {
    return (
      <div className="govuk-width-container govuk-main-wrapper flex justify-center">
        <Loader2 className="animate-spin" />
      </div>
    )
  }

  if (!template) {
    notFound()
  }

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
      <div className="govuk-grid-row">
        <div className="govuk-grid-column-one-half">
          <h1 className="govuk-heading-xl">{template.name}</h1>
          <ul className="govuk-list flex gap-2">
            {template.is_default && (
              <li>
                <span className="govuk-tag govuk-tag--blue govuk-!-margin-bottom-3">
                  Default
                </span>
              </li>
            )}
            <li>
              <span className="govuk-tag govuk-tag--grey govuk-!-margin-bottom-3">
                System
              </span>
            </li>
            <li>
              <span className="govuk-tag govuk-tag--green govuk-!-margin-bottom-3">
                Summary
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
                  body: template.is_default
                    ? {}
                    : { template_name: template.name },
                })
              }
            >
              {template.is_default ? (
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
          </div>
        </div>
      </div>
      <div className="govuk-grid-row govuk-!-margin-bottom-6 border-b border-(--govuk-border-colour)">
        <div className="govuk-grid-column-full">
          <p className="govuk-body-l">{template.description}</p>
        </div>
      </div>
      <div className="govuk-grid-row">
        <div className="govuk-grid-column-full">
          <p className="govuk-body">
            This is a built-in template. It can be set as your default but
            cannot be edited, renamed, or deleted.
          </p>
        </div>
      </div>
    </div>
  )
}
