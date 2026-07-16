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
import { useEffect } from 'react'

import {
  EditorToolbar,
  ToolbarItem,
  toolbarItems,
} from '@/components/editor/editor-toolbar'
import { CitationPopoverWrapper } from '@/components/ui/citation-popover-wrapper'
import { useCitationPopover } from '@/hooks/use-citation-popover'
import { citationRegex, citationRegexWithSpace } from '@/lib/citationRegex'
import { Transcription } from '@/lib/client'
import { cn } from '@/lib/utils'
import posthog from 'posthog-js'

const MINUTE_TOOLBAR_ITEMS: ToolbarItem[] = [
  toolbarItems.undo,
  toolbarItems.redo,
  { ...toolbarItems.bold, startsGroup: true },
  toolbarItems.italic,
  toolbarItems.strikethrough,
  { ...toolbarItems.code, startsGroup: true },
  { ...toolbarItems.bulletList, startsGroup: true },
  toolbarItems.orderedList,
  toolbarItems.heading(3),
]

function SimpleEditor({
  initialContent,
  onContentChange,
  isEditing,
  currentTranscription,
  hideCitations,
}: {
  initialContent: string
  onContentChange: (newContent: string) => void
  isEditing: boolean
  currentTranscription: Transcription
  hideCitations: boolean
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
              const citationRegex = citationRegexWithSpace

              state.doc.descendants((node, pos) => {
                if (node.isText) {
                  let match

                  while ((match = citationRegex.exec(node.text!)) !== null) {
                    const from = pos + match.index
                    const to = from + match[0].length
                    decorations.push(
                      Decoration.inline(from, to, {
                        style: 'display: var(--citation-display);',
                      })
                    )
                    decorations.push(
                      Decoration.inline(from + match[1].length, to, {
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
                  const match = domNode.textContent?.match(citationRegex)
                  if (match) {
                    const index = parseInt(match[1], 10)
                    posthog.capture('citation_clicked', {
                      citationIndex: index,
                    })
                    handleCitationClick(index)
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

  if (!editorObject) {
    return null
  }

  return (
    <div>
      {isEditing && (
        <EditorToolbar
          editor={editorObject}
          items={MINUTE_TOOLBAR_ITEMS}
          className="sticky top-[105px] z-10"
        />
      )}

      <div
        className={cn(
          isEditing &&
            'govuk-!-padding-2 border border-2 border-(--govuk-input-border-colour) bg-white'
        )}
      >
        <EditorContent
          editor={editorObject}
          className={cn('editor-content')}
          style={
            {
              '--citation-display': hideCitations ? 'none' : 'unset',
            } as React.CSSProperties
          }
        />
      </div>

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
