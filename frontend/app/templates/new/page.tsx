'use client'

import { TemplateEditor } from '@/app/templates/components/editor/template-editor'
import { createUserTemplateUserTemplatesPostMutation } from '@/lib/client/@tanstack/react-query.gen'
import { useMutation } from '@tanstack/react-query'
import { useRouter } from 'next/navigation'

export default function NewTemplatePage() {
  const navigation = useRouter()
  const { mutate } = useMutation({
    ...createUserTemplateUserTemplatesPostMutation(),
    onSuccess: () => {
      navigation.push('/templates')
    },
  })
  return (
    <div>
      <h1 className="mb-6 text-3xl font-bold">New template</h1>
      <TemplateEditor
        onSubmit={(body) => {
          mutate({ body })
        }}
      />
    </div>
  )
}
