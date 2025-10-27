'use client'

import { TemplateEditorToolbar } from '@/app/templates/components/editor/editor-toolbar'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { TemplateData } from '@/types/templates'
import Document from '@tiptap/extension-document'
import HardBreak from '@tiptap/extension-hard-break'
import Paragraph from '@tiptap/extension-paragraph'
import Text from '@tiptap/extension-text'
import { EditorContent, useEditor } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import { Loader2, Save } from 'lucide-react'
import { useEffect } from 'react'
import { Controller, useFormContext } from 'react-hook-form'

export const DocumentTemplateEditor = ({
  onSubmit,
}: {
  onSubmit: (data: TemplateData) => void
}) => {
  const form = useFormContext<TemplateData>()
  return (
    <form
      className="flex flex-col gap-4"
      onSubmit={form.handleSubmit(onSubmit)}
    >
      <div className="flex gap-2">
        <Button type="submit">
          <Save /> Save
        </Button>
        {form.formState.isSubmitting && (
          <div>
            <Loader2 className="animate-spin" />
            Submitting...
          </div>
        )}
        <div className="flex-1 text-xs text-red-600">
          <p>
            {form.formState.errors.content?.message
              ? form.formState.errors.content.message
              : null}
          </p>
          <p>
            {form.formState.errors.name?.message
              ? form.formState.errors.name?.message
              : null}
          </p>
          <p>
            {form.formState.errors.description?.message
              ? form.formState.errors.description?.message
              : null}
          </p>
        </div>
      </div>
      <div>
        <Label htmlFor="name">Template Name</Label>
        <Input
          {...form.register('name')}
          className="mt-2"
          placeholder="Name your template"
        />
      </div>
      <div>
        <Label htmlFor="name">Description</Label>
        <Textarea
          {...form.register('description', {
            required: { value: true, message: 'Description required' },
          })}
          className="mt-2"
          placeholder="A description to help identify the template."
        />
      </div>
      <Controller
        name="content"
        control={form.control}
        rules={{
          required: { value: true, message: 'Template content required.' },
        }}
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
