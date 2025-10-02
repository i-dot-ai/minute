'use client'

import { TemplateEditorToolbar } from '@/app/templates/components/editor/editor-toolbar'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { useTabCloseWarning } from '@/hooks/use-tab-close-warning'
import Document from '@tiptap/extension-document'
import HardBreak from '@tiptap/extension-hard-break'
import Paragraph from '@tiptap/extension-paragraph'
import Text from '@tiptap/extension-text'
import { EditorContent, useEditor } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import { Save } from 'lucide-react'
import { useEffect } from 'react'
import { Controller, useForm } from 'react-hook-form'

export type TemplateData = {
  name: string
  content: string
  description: string
}

export function TemplateEditor({
  defaultValues,
  onSubmit,
}: {
  defaultValues?: { name: string; content: string; description: string }
  onSubmit: (data: TemplateData) => void
}) {
  const form = useForm<TemplateData>({ defaultValues })

  useEffect(() => {
    if (
      defaultValues &&
      defaultValues.content != form.getValues('content') &&
      defaultValues.description != form.getValues('description') &&
      defaultValues.name != form.getValues('name')
    ) {
      form.setValue('name', defaultValues.name, { shouldDirty: true })
      form.setValue('content', defaultValues.content, { shouldDirty: true })
      form.setValue('description', defaultValues.description, {
        shouldDirty: true,
      })
    }
  }, [defaultValues, form])

  useEffect(() => {
    if (form.formState.isSubmitSuccessful) {
      form.reset(form.getValues(), { keepValues: true })
    }
  }, [form, form.formState.isSubmitSuccessful])
  useTabCloseWarning(
    form.formState.isDirty
      ? 'Your changes to the template have not been saved.'
      : false
  )
  return (
    <form
      onSubmit={form.handleSubmit(onSubmit)}
      className="flex flex-col gap-4"
    >
      <div className="flex">
        <Button type="submit" disabled={!form.formState.isDirty}>
          <Save />
          {!form.formState.isDirty
            ? 'Saved'
            : form.formState.isLoading
              ? 'Saving'
              : 'Save'}
        </Button>
      </div>
      <div>
        <Label htmlFor="name">Template Name</Label>
        <Input {...form.register('name')} className="mt-2" />
      </div>
      <div>
        <Label htmlFor="name">Description</Label>
        <Textarea {...form.register('description')} className="mt-2" />
      </div>
      <Controller
        name="content"
        control={form.control}
        render={({ field: { onChange, value } }) => (
          <ControlledEditor onChange={onChange} value={value} />
        )}
      />
    </form>
  )
}

const ControlledEditor = ({
  onChange,
  value,
}: {
  onChange: (v: string) => void
  value: string
}) => {
  const editor = useEditor({
    extensions: [StarterKit, Document, Paragraph, Text, HardBreak],
    onUpdate: ({ editor }) => {
      onChange(editor.getHTML())
    },
    content: value,
  })

  useEffect(() => {
    if (editor && value !== editor.getHTML()) {
      editor.commands.setContent(value || '')
    }
  }, [editor, value])
  return (
    <div>
      <Label htmlFor="content">Template Content</Label>
      <div className="mt-2">
        <TemplateEditorToolbar editor={editor} />
        <div className="rounded-xl rounded-t-none border border-t-0 shadow">
          <EditorContent editor={editor} className="editor-content" />
        </div>
      </div>
    </div>
  )
}
