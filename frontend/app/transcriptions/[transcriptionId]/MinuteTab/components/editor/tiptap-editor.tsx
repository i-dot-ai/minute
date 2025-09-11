'use client'

import { Extension } from '@tiptap/core'
import Document from '@tiptap/extension-document'
import HardBreak from '@tiptap/extension-hard-break'
import Paragraph from '@tiptap/extension-paragraph'
import Text from '@tiptap/extension-text'
import type { Editor } from '@tiptap/react'
import { EditorContent, useEditor } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import { EditorState, Plugin, PluginKey } from 'prosemirror-state'
import { Decoration, DecorationSet } from 'prosemirror-view'
import { useCallback, useEffect } from 'react'

import { Transcription } from '@/lib/client'
import { cn } from '@/lib/utils'
import posthog from 'posthog-js'
import {
  Bold as BoldIcon,
  Code as CodeIcon,
  Italic as ItalicIcon,
  ListOrdered as OrderedListIcon,
  RotateLeft,
  RotateRight,
  Strikethrough as StrikethroughIcon,
  List as UnorderedListIcon,
} from './Icons'
import { useCitationPopover } from '@/hooks/use-citation-popover'
import { CitationPopoverWrapper } from '@/components/ui/citation-popover-wrapper'

function SimpleEditor({
  initialContent,
  onContentChange,
  isEditing,
  currentTranscription,
}: {
  initialContent: string
  onContentChange: (newContent: string) => void
  isEditing: boolean
  currentTranscription: Transcription
}) {
  const {
    citationPopover,
    isPopoverOpen,
    handleCitationClick,
    closeCitationPopover,
    setIsPopoverOpen,
  } = useCitationPopover()

  const CitationExtension = Extension.create({
    name: 'citation',
    addProseMirrorPlugins() {
      return [
        new Plugin({
          key: new PluginKey('citation'),
          props: {
            decorations(state) {
              const decorations: Decoration[] = []
              const citationRegex = /\[(\d+)\]/g

              state.doc.descendants((node, pos) => {
                if (node.isText) {
                  let match

                  while ((match = citationRegex.exec(node.text!)) !== null) {
                    const from = pos + match.index
                    const to = from + match[0].length
                    decorations.push(
                      Decoration.inline(from, to, {
                        class: 'citation-link',
                        style:
                          'color: blue; cursor: pointer; text-decoration: underline;',
                      })
                    )
                  }
                }
              })

              return DecorationSet.create(state.doc, decorations)
            },
            handleDOMEvents: {
              click: (view, event) => {
                const pos = view.posAtDOM(event.target as Node, 0)
                if (pos === null) return false

                const domNode = event.target as HTMLElement

                if (domNode.classList.contains('citation-link')) {
                  const match = domNode.textContent?.match(/\[(\d+)\]/)
                  if (match) {
                    const index = parseInt(match[1], 10)
                    const rect = domNode.getBoundingClientRect()
                    posthog.capture('citation_clicked', {
                      citationIndex: index,
                    })
                    handleCitationClick(index, rect)
                    return true
                  }
                }
                return false
              },
            },
          },
        }),
      ]
    },
  })

  const editorObject = useEditor({
    extensions: [
      StarterKit,
      Document,
      Paragraph,
      Text,
      CitationExtension,
      HardBreak,
    ],
    onUpdate: ({ editor }) => {
      onContentChange(editor.getHTML())
    },
    content: initialContent,
  }) as Editor

  useEffect(() => {
    if (editorObject) {
      editorObject.setEditable(isEditing)
    }
  }, [editorObject, isEditing])

  useEffect(() => {
    if (editorObject && initialContent !== editorObject.getHTML()) {
      editorObject.commands.setContent(initialContent)
      const newEditorState = EditorState.create({
        doc: editorObject.state.doc,
        plugins: editorObject.state.plugins,
        schema: editorObject.state.schema,
      })
      editorObject.view.updateState(newEditorState)
    }
  }, [editorObject, initialContent])

  const toggleBold = useCallback(() => {
    editorObject.chain().focus().toggleBold().run()
  }, [editorObject])

  const toggleItalic = useCallback(() => {
    editorObject.chain().focus().toggleItalic().run()
  }, [editorObject])

  const toggleStrike = useCallback(() => {
    editorObject.chain().focus().toggleStrike().run()
  }, [editorObject])

  const toggleCode = useCallback(() => {
    editorObject.chain().focus().toggleCode().run()
  }, [editorObject])

  const toggleBulletList = useCallback(() => {
    editorObject.chain().focus().toggleBulletList().run()
  }, [editorObject])

  const toggleOrderedList = useCallback(() => {
    editorObject.chain().focus().toggleOrderedList().run()
  }, [editorObject])

  if (!editorObject) {
    return null
  }

  return (
    <div className="relative rounded-md border border-gray-300">
      {isEditing && (
        <div className="flex items-center justify-between border-b border-gray-300 bg-gray-50 p-2">
          <div className="flex items-center">
            <div className="mr-4 flex space-x-1">
              <button
                className="rounded p-1 hover:bg-gray-200 disabled:opacity-50"
                onClick={() => editorObject.chain().focus().undo().run()}
                disabled={!editorObject.can().undo()}
                type="button"
              >
                <RotateLeft size={20} />
              </button>
              <button
                className="rounded p-1 hover:bg-gray-200 disabled:opacity-50"
                onClick={() => editorObject.chain().focus().redo().run()}
                disabled={!editorObject.can().redo()}
                type="button"
              >
                <RotateRight size={20} />
              </button>
            </div>
            <div className="mr-4 flex space-x-1">
              <button
                className={cn('rounded p-1 hover:bg-gray-200', {
                  'bg-gray-300': editorObject.isActive('bold'),
                })}
                onClick={toggleBold}
                type="button"
              >
                <BoldIcon size={20} />
              </button>
              <button
                className={cn('rounded p-1 hover:bg-gray-200', {
                  'bg-gray-300': editorObject.isActive('italic'),
                })}
                onClick={toggleItalic}
                type="button"
              >
                <ItalicIcon size={20} />
              </button>

              <button
                className={cn('rounded p-1 hover:bg-gray-200', {
                  'bg-gray-300': editorObject.isActive('strike'),
                })}
                onClick={toggleStrike}
                type="button"
              >
                <StrikethroughIcon size={20} />
              </button>
            </div>
            <div className="mr-4 flex space-x-1">
              <button
                className={cn('rounded p-1 hover:bg-gray-200', {
                  'bg-gray-300': editorObject.isActive('code'),
                })}
                onClick={toggleCode}
                type="button"
              >
                <CodeIcon size={20} />
              </button>
            </div>
            <div className="flex space-x-1">
              <button
                className={cn('rounded p-1 hover:bg-gray-200', {
                  'bg-gray-300': editorObject.isActive('bulletList'),
                })}
                onClick={toggleBulletList}
                type="button"
              >
                <UnorderedListIcon size={20} />
              </button>
              <button
                className={cn('rounded p-1 hover:bg-gray-200', {
                  'bg-gray-300': editorObject.isActive('orderedList'),
                })}
                onClick={toggleOrderedList}
                type="button"
              >
                <OrderedListIcon size={20} />
              </button>
              <button
                className={cn('rounded p-1 hover:bg-gray-200', {
                  'bg-gray-300': editorObject.isActive('heading', { level: 3 }),
                })}
                onClick={() =>
                  editorObject.chain().focus().toggleHeading({ level: 3 }).run()
                }
                type="button"
              >
                H3
              </button>
            </div>
          </div>
        </div>
      )}

      <EditorContent editor={editorObject} className={cn('editor-content')} />

      {citationPopover && (
        <CitationPopoverWrapper
          citationPopover={citationPopover}
          isPopoverOpen={isPopoverOpen}
          onOpenChange={(open) => {
            setIsPopoverOpen(open)
            if (!open) closeCitationPopover()
          }}
          transcription={currentTranscription}
        />
      )}
    </div>
  )
}

export default SimpleEditor
