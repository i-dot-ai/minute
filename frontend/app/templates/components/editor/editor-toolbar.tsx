'use client'

import {
  EditorToolbar,
  ToolbarItem,
  toolbarItems,
} from '@/components/editor/editor-toolbar'
import { Editor } from '@tiptap/core'

const TEMPLATE_TOOLBAR_ITEMS: ToolbarItem[] = [
  toolbarItems.bold,
  toolbarItems.italic,
  toolbarItems.strikethrough,
  toolbarItems.code,
  { ...toolbarItems.heading(1), startsGroup: true },
  toolbarItems.heading(2),
  toolbarItems.heading(3),
  toolbarItems.heading(4),
  { ...toolbarItems.bulletList, startsGroup: true },
  toolbarItems.orderedList,
  { ...toolbarItems.undo, startsGroup: true },
  toolbarItems.redo,
]

export const TemplateEditorToolbar = ({ editor }: { editor: Editor | null }) => (
  <EditorToolbar editor={editor} items={TEMPLATE_TOOLBAR_ITEMS} />
)
