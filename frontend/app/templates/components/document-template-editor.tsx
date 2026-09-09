'use client'

import { TemplateEditorToolbar } from '@/app/templates/components/editor/editor-toolbar'
import { TemplateData } from '@/types/templates'
import Document from '@tiptap/extension-document'
import HardBreak from '@tiptap/extension-hard-break'
import Paragraph from '@tiptap/extension-paragraph'
import Text from '@tiptap/extension-text'
import { EditorContent, useEditor } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import { useEffect } from 'react'
import { Controller, useFormContext } from 'react-hook-form'

export const DocumentTemplateEditor = () => {
  const form = useFormContext<TemplateData>()
  return (
    <div className="govuk-form-group">
      <h2>
        <label className="govuk-label govuk-label--s" htmlFor="content">
          Template content
        </label>
      </h2>
      <div id="content-hint" className="govuk-hint">
        The template content should look how you would like the minutes to look.
        Use placeholder text to describe what you would like in each section and
        provide style guidance, including examples if necessary. You may need to
        iterate on your template to get the best results.
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
      <div className="border border-2 border-t-0 border-(--govuk-input-border-colour) bg-white">
        <EditorContent editor={editor} className="editor-content" />
      </div>
    </div>
  )
}
