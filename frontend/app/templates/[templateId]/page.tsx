'use client'

import { TemplateEditor } from '@/app/templates/components/editor/template-editor'
import { NavButton } from '@/components/layout/nav-button'
import {
  editUserTemplateUserTemplatesTemplateIdPatchMutation,
  getUserTemplateUserTemplatesTemplateIdGetOptions,
  getUserTemplateUserTemplatesTemplateIdGetQueryKey,
} from '@/lib/client/@tanstack/react-query.gen'
import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query'
import { ArrowLeft, Loader2 } from 'lucide-react'

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
  if (!template) {
    return <Loader2 className="animate-spin" />
  }
  return (
    <div>
      <NavButton href="/templates">
        <ArrowLeft />
        Back
      </NavButton>
      <h1 className="mb-6 text-3xl font-bold">Edit template</h1>
      <TemplateEditor
        defaultValues={{
          name: template.name,
          content: template.content,
          description: template.description || '',
        }}
        onSubmit={(data) =>
          mutate({ path: { template_id: templateId }, body: data })
        }
      />
    </div>
  )
}
