'use client'

import { TemplateEditorToolbar } from '@/app/templates/components/editor/editor-toolbar'
import { ExampleTemplatesDialog } from '@/app/templates/components/example-templates-dialog'
import { exampleDocumentTemplates } from '@/app/templates/data/example-templates'
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
    <form onSubmit={form.handleSubmit(onSubmit)}>
      <div className="govuk-button-group">
        <button type="submit" className="govuk-button">
          <Save className="size-4" /> Save
        </button>
        <ExampleTemplatesDialog
          examples={exampleDocumentTemplates}
          onSelectTemplate={(template) => form.reset(template)}
        />
        {form.formState.isSubmitting && (
          <p className="govuk-body">
            <Loader2 className="animate-spin" />
            Submitting...
          </p>
        )}
        <div className="text-red-600">
          <p className="govuk-body">
            {form.formState.errors.content?.message
              ? form.formState.errors.content.message
              : null}
          </p>
          <p className="govuk-body">
            {form.formState.errors.name?.message
              ? form.formState.errors.name?.message
              : null}
          </p>
          <p className="govuk-body">
            {form.formState.errors.description?.message
              ? form.formState.errors.description?.message
              : null}
          </p>
        </div>
      </div>
      <h2 className="govuk-heading-l">Template details</h2>
      <p className="govuk-body">
        Add a name and description so you can find your template later. Name
        and description are not used to generate your minute, any structure
        and style instructions should be added to the template content
        field.
      </p>
      <div className="govuk-form-group">
        <label className="govuk-label govuk-label--m" htmlFor="name">
          Template name
        </label>
        <div id="name-hint" className="govuk-hint">
          A short memorable name to help you find this template later.
        </div>
        <input className="govuk-input" id="name" type="text" {...form.register('name')} />
      </div>

      <div className="govuk-form-group">
        <label className="govuk-label govuk-label--m" htmlFor="description">
          Description
        </label>
        <div id="description-hint" className="govuk-hint">
          A description to help identify the template - for example, who&apos;s it for or when to use it.
        </div>
        <textarea
          className="govuk-textarea"
          id="description"
          rows={10}
          {...form.register('description', {
            required: { value: true, message: 'Description required' },
          })}
        />
      </div>
      <div className="govuk-form-group">
        <h2>
          <label className="govuk-label govuk-label--l" htmlFor="content">
            Template content
          </label>
        </h2>
        <div id="content-hint" className="govuk-hint">
          The template content should look how you would like the minutes to
          look. Use placeholder text to describe what you would like in each
          section and provide style guidance, including examples if necessary. You may need to iterate on your template to get the best results.
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
      <div className="border border-2 border-(--govuk-input-border-colour)">
        <EditorContent editor={editor} className="editor-content" />
      </div>
    </div>
  )
}
