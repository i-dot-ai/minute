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
  LucideIcon,
} from 'lucide-react'
import { useRef, useState } from 'react'

interface TemplateEditorToolbarProps {
  editor: Editor | null
}

interface ToolbarItem {
  label: string
  icon: LucideIcon
  run: (editor: Editor) => void
  isActive?: (editor: Editor) => boolean
  isDisabled?: (editor: Editor) => boolean
  startsGroup?: boolean
}

const TOOLBAR_ITEMS: ToolbarItem[] = [
  {
    label: 'Bold',
    icon: Bold,
    run: (editor) => editor.chain().focus().toggleBold().run(),
    isActive: (editor) => editor.isActive('bold'),
  },
  {
    label: 'Italic',
    icon: Italic,
    run: (editor) => editor.chain().focus().toggleItalic().run(),
    isActive: (editor) => editor.isActive('italic'),
  },
  {
    label: 'Strikethrough',
    icon: Strikethrough,
    run: (editor) => editor.chain().focus().toggleStrike().run(),
    isActive: (editor) => editor.isActive('strike'),
  },
  {
    label: 'Code',
    icon: Code,
    run: (editor) => editor.chain().focus().toggleCode().run(),
    isActive: (editor) => editor.isActive('code'),
  },
  {
    label: 'Heading level 1',
    icon: Heading1,
    run: (editor) => editor.chain().focus().toggleHeading({ level: 1 }).run(),
    isActive: (editor) => editor.isActive('heading', { level: 1 }),
    startsGroup: true,
  },
  {
    label: 'Heading level 2',
    icon: Heading2,
    run: (editor) => editor.chain().focus().toggleHeading({ level: 2 }).run(),
    isActive: (editor) => editor.isActive('heading', { level: 2 }),
  },
  {
    label: 'Heading level 3',
    icon: Heading3,
    run: (editor) => editor.chain().focus().toggleHeading({ level: 3 }).run(),
    isActive: (editor) => editor.isActive('heading', { level: 3 }),
  },
  {
    label: 'Heading level 4',
    icon: Heading4,
    run: (editor) => editor.chain().focus().toggleHeading({ level: 4 }).run(),
    isActive: (editor) => editor.isActive('heading', { level: 4 }),
  },
  {
    label: 'Bullet list',
    icon: List,
    run: (editor) => editor.chain().focus().toggleBulletList().run(),
    isActive: (editor) => editor.isActive('bulletList'),
    startsGroup: true,
  },
  {
    label: 'Numbered list',
    icon: ListOrdered,
    run: (editor) => editor.chain().focus().toggleOrderedList().run(),
    isActive: (editor) => editor.isActive('orderedList'),
  },
  {
    label: 'Undo',
    icon: Undo,
    run: (editor) => editor.chain().focus().undo().run(),
    isDisabled: (editor) => !editor.can().chain().focus().undo().run(),
    startsGroup: true,
  },
  {
    label: 'Redo',
    icon: Redo,
    run: (editor) => editor.chain().focus().redo().run(),
    isDisabled: (editor) => !editor.can().chain().focus().redo().run(),
  },
]

export const TemplateEditorToolbar = ({
  editor,
}: TemplateEditorToolbarProps) => {
  const [focusedIndex, setFocusedIndex] = useState(0)
  const buttonRefs = useRef<(HTMLButtonElement | null)[]>([])

  if (!editor) {
    return null
  }

  const moveFocus = (index: number) => {
    setFocusedIndex(index)
    buttonRefs.current[index]?.focus()
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    const last = TOOLBAR_ITEMS.length - 1
    switch (e.key) {
      case 'ArrowRight':
        moveFocus(focusedIndex === last ? 0 : focusedIndex + 1)
        break
      case 'ArrowLeft':
        moveFocus(focusedIndex === 0 ? last : focusedIndex - 1)
        break
      case 'Home':
        moveFocus(0)
        break
      case 'End':
        moveFocus(last)
        break
      default:
        return
    }
    e.preventDefault()
  }

  return (
    <Card className="rounded-none border border-2 border-b-0 border-(--govuk-input-border-colour) p-2">
      <div
        role="toolbar"
        aria-label="Text formatting"
        className="flex flex-wrap gap-1"
        onKeyDown={handleKeyDown}
      >
        {TOOLBAR_ITEMS.map((item, index) => {
          const Icon = item.icon
          const active = item.isActive?.(editor) ?? false
          const disabled = item.isDisabled?.(editor) ?? false
          return (
            <div key={item.label} className="flex gap-1">
              {item.startsGroup && <div className="mx-1 h-6 w-px bg-gray-300" />}
              <Button
                ref={(el) => {
                  buttonRefs.current[index] = el
                }}
                type="button"
                variant={active ? 'secondary' : 'ghost'}
                size="sm"
                aria-label={item.label}
                aria-pressed={item.isActive ? active : undefined}
                aria-disabled={disabled || undefined}
                className="aria-disabled:pointer-events-none aria-disabled:opacity-50"
                tabIndex={index === focusedIndex ? 0 : -1}
                onFocus={() => setFocusedIndex(index)}
                onClick={() => {
                  if (!disabled) item.run(editor)
                }}
              >
                <Icon />
              </Button>
            </div>
          )
        })}
      </div>
    </Card>
  )
}
