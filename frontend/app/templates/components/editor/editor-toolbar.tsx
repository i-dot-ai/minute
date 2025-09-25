'use client'

import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Editor } from '@tiptap/core'
import {
  Bold,
  Code,
  Heading1,
  Heading2,
  Heading3,
  Heading4,
  Italic,
  List,
  ListOrdered,
  Redo,
  Strikethrough,
  Undo,
} from 'lucide-react'

interface TemplateEditorToolbarProps {
  editor: Editor | null
}

export const TemplateEditorToolbar = ({
  editor,
}: TemplateEditorToolbarProps) => {
  if (!editor) {
    return null
  }

  return (
    <Card className="rounded-b-none border-b-0 p-2">
      <div className="flex flex-wrap gap-1">
        <Button
          type="button"
          variant={editor.isActive('bold') ? 'secondary' : 'ghost'}
          size="sm"
          onClick={() => editor.chain().focus().toggleBold().run()}
        >
          <Bold />
        </Button>
        <Button
          type="button"
          variant={editor.isActive('italic') ? 'secondary' : 'ghost'}
          size="sm"
          onClick={() => editor.chain().focus().toggleItalic().run()}
        >
          <Italic />
        </Button>
        <Button
          type="button"
          variant={editor.isActive('strike') ? 'secondary' : 'ghost'}
          size="sm"
          onClick={() => editor.chain().focus().toggleStrike().run()}
        >
          <Strikethrough />
        </Button>
        <Button
          type="button"
          variant={editor.isActive('code') ? 'secondary' : 'ghost'}
          size="sm"
          onClick={() => editor.chain().focus().toggleCode().run()}
        >
          <Code />
        </Button>
        <div className="mx-1 h-6 w-px bg-gray-300" />
        <Button
          type="button"
          variant={
            editor.isActive('heading', { level: 1 }) ? 'secondary' : 'ghost'
          }
          size="sm"
          onClick={() =>
            editor.chain().focus().toggleHeading({ level: 1 }).run()
          }
        >
          <Heading1 />
        </Button>
        <Button
          type="button"
          variant={
            editor.isActive('heading', { level: 2 }) ? 'secondary' : 'ghost'
          }
          size="sm"
          onClick={() =>
            editor.chain().focus().toggleHeading({ level: 2 }).run()
          }
        >
          <Heading2 />
        </Button>
        <Button
          type="button"
          variant={
            editor.isActive('heading', { level: 3 }) ? 'secondary' : 'ghost'
          }
          size="sm"
          onClick={() =>
            editor.chain().focus().toggleHeading({ level: 3 }).run()
          }
        >
          <Heading3 />
        </Button>
        <Button
          type="button"
          variant={
            editor.isActive('heading', { level: 4 }) ? 'secondary' : 'ghost'
          }
          size="sm"
          onClick={() =>
            editor.chain().focus().toggleHeading({ level: 4 }).run()
          }
        >
          <Heading4 />
        </Button>
        <div className="mx-1 h-6 w-px bg-gray-300" />
        <Button
          type="button"
          variant={editor.isActive('bulletList') ? 'secondary' : 'ghost'}
          size="sm"
          onClick={() => editor.chain().focus().toggleBulletList().run()}
        >
          <List />
        </Button>
        <Button
          type="button"
          variant={editor.isActive('orderedList') ? 'secondary' : 'ghost'}
          size="sm"
          onClick={() => editor.chain().focus().toggleOrderedList().run()}
        >
          <ListOrdered />
        </Button>
        <div className="mx-1 h-6 w-px bg-gray-300" />
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={() => editor.chain().focus().undo().run()}
          disabled={!editor.can().chain().focus().undo().run()}
        >
          <Undo />
        </Button>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={() => editor.chain().focus().redo().run()}
          disabled={!editor.can().chain().focus().redo().run()}
        >
          <Redo />
        </Button>
      </div>
    </Card>
  )
}
