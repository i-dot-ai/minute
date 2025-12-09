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
      <div className="flex flex-col gap-4 rounded-lg border p-4">
        <div>
          <h4 className="font-semibold">Template details</h4>
          <p className="text-muted-foreground text-sm">
            Add a name and description so you can find your template later. Name
            and description are not used to generate your minute, any structure
            and style instructions should be added to the template content
            field.
          </p>
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
      </div>
      <div className="rounded-md border p-4">
        <Label htmlFor="content" className="text-md font-semibold">
          Template Content
        </Label>
        <p className="text-muted-foreground mt-1 mb-2 text-sm">
          The template content should look how you would like the minutes to
          look. Use placeholder text to describe what you would like in each
          section and provide style guidance, including examples if necessary.
          You may need to iterate on your template to get the best results.
        </p>
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
      </div>
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
      <TemplateEditorToolbar editor={editor} />
      <div className="rounded-xl rounded-t-none border border-t-0 shadow">
        <EditorContent editor={editor} className="editor-content" />
      </div>
    </div>
  )
}
