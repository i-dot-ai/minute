'use client'

import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import type { Editor } from '@tiptap/core'
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
  LucideIcon,
  Redo,
  Strikethrough,
  Undo,
} from 'lucide-react'
import { useRef, useState } from 'react'

export interface ToolbarItem {
  label: string
  icon: LucideIcon
  run: (editor: Editor) => void
  isActive?: (editor: Editor) => boolean
  isDisabled?: (editor: Editor) => boolean
  startsGroup?: boolean
}

const headingIcons: Record<number, LucideIcon> = {
  1: Heading1,
  2: Heading2,
  3: Heading3,
  4: Heading4,
}

/**
 * Shared catalogue of toolbar buttons so every editor uses identical labels,
 * icons, and commands. Editors compose their own item lists from these
 * (spread and set `startsGroup: true` to draw a separator before an item).
 */
export const toolbarItems = {
  bold: {
    label: 'Bold',
    icon: Bold,
    run: (editor) => editor.chain().focus().toggleBold().run(),
    isActive: (editor) => editor.isActive('bold'),
  },
  italic: {
    label: 'Italic',
    icon: Italic,
    run: (editor) => editor.chain().focus().toggleItalic().run(),
    isActive: (editor) => editor.isActive('italic'),
  },
  strikethrough: {
    label: 'Strikethrough',
    icon: Strikethrough,
    run: (editor) => editor.chain().focus().toggleStrike().run(),
    isActive: (editor) => editor.isActive('strike'),
  },
  code: {
    label: 'Code',
    icon: Code,
    run: (editor) => editor.chain().focus().toggleCode().run(),
    isActive: (editor) => editor.isActive('code'),
  },
  heading: (level: 1 | 2 | 3 | 4): ToolbarItem => ({
    label: `Heading level ${level}`,
    icon: headingIcons[level],
    run: (editor) => editor.chain().focus().toggleHeading({ level }).run(),
    isActive: (editor) => editor.isActive('heading', { level }),
  }),
  bulletList: {
    label: 'Bullet list',
    icon: List,
    run: (editor) => editor.chain().focus().toggleBulletList().run(),
    isActive: (editor) => editor.isActive('bulletList'),
  },
  orderedList: {
    label: 'Numbered list',
    icon: ListOrdered,
    run: (editor) => editor.chain().focus().toggleOrderedList().run(),
    isActive: (editor) => editor.isActive('orderedList'),
  },
  undo: {
    label: 'Undo',
    icon: Undo,
    run: (editor) => editor.chain().focus().undo().run(),
    isDisabled: (editor) => !editor.can().chain().focus().undo().run(),
  },
  redo: {
    label: 'Redo',
    icon: Redo,
    run: (editor) => editor.chain().focus().redo().run(),
    isDisabled: (editor) => !editor.can().chain().focus().redo().run(),
  },
} satisfies Record<string, ToolbarItem | ((level: 1 | 2 | 3 | 4) => ToolbarItem)>

/**
 * WAI-ARIA toolbar: a single tab stop with roving tabindex, arrow-key
 * navigation, and Home/End. Styled to sit flush on top of a bordered
 * editor box (no bottom border).
 */
export const EditorToolbar = ({
  editor,
  items,
  className,
}: {
  editor: Editor | null
  items: ToolbarItem[]
  className?: string
}) => {
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
    const last = items.length - 1
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
    <Card
      className={cn(
        'rounded-none border border-2 border-b-0 border-(--govuk-input-border-colour) p-2',
        className
      )}
    >
      <div
        role="toolbar"
        aria-label="Text formatting"
        className="flex flex-wrap gap-1"
        onKeyDown={handleKeyDown}
      >
        {items.map((item, index) => {
          const Icon = item.icon
          const active = item.isActive?.(editor) ?? false
          const disabled = item.isDisabled?.(editor) ?? false
          return (
            <div key={item.label} className="flex gap-1">
              {item.startsGroup && (
                <div className="mx-1 h-6 w-px bg-gray-300" />
              )}
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
