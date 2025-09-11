'use client'

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import { Button } from '@/components/ui/button'
import { CitationPopoverWrapper } from '@/components/ui/citation-popover-wrapper'
import { Textarea } from '@/components/ui/textarea'
import { useCitationPopover } from '@/hooks/use-citation-popover'
import type { ChatGetResponse } from '@/lib/client'
import * as api from '@/lib/client' // Import the API client for direct calls
import { Transcription } from '@/lib/client'
import {
  createChatTranscriptionsTranscriptionIdChatPostMutation,
  deleteChatsTranscriptionsTranscriptionIdChatDeleteMutation,
  getChatTranscriptionsTranscriptionIdChatChatIdGetQueryKey,
  listChatTranscriptionsTranscriptionIdChatGetOptions,
  listChatTranscriptionsTranscriptionIdChatGetQueryKey,
} from '@/lib/client/@tanstack/react-query.gen'
import { CitationContent, linkCitations } from '@/utils/citation-renderer'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Loader2, MessageCircle, SendHorizontal, Trash2 } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import Markdown from 'react-markdown'

export function ChatTab({ transcription }: { transcription: Transcription }) {
  const transcriptionId = transcription.id!
  const queryClient = useQueryClient()
  const [input, setInput] = useState('')
  const listEndRef = useRef<HTMLDivElement | null>(null)
  const [pollingChatId, setPollingChatId] = useState<string | null>(null) // State to hold the ID of the chat message to poll

  const {
    citationPopover,
    isPopoverOpen,
    handleCitationClick,
    closeCitationPopover,
    setIsPopoverOpen,
  } = useCitationPopover()

  const renderMessageContent = (
    role: 'user' | 'assistant',
    content: string
  ) => {
    if (role !== 'assistant') return content
    return linkCitations(content)
  }

  // Main query to fetch the list of chat messages
  // RefetchInterval removed here, as individual messages will be polled
  const { data, isLoading } = useQuery({
    ...listChatTranscriptionsTranscriptionIdChatGetOptions({
      path: { transcription_id: transcriptionId },
    }),
    // refetchInterval is removed from here. Polling will be handled by a separate query.
  })

  const chatItems: ChatGetResponse[] = useMemo(
    () => (data?.chat as ChatGetResponse[]) ?? [],
    [data?.chat]
  )

  // Effect to find the latest 'in_progress' or 'awaiting_start' chat item
  // and set it for individual polling.
  useEffect(() => {
    // Filter out optimistic (temporary) IDs before searching for an item to poll.
    // We only want to poll messages that have a real ID from the server.
    const realChatItems = chatItems.filter(
      (item) => item.id && !item.id.startsWith('optimistic-')
    )

    const chatItemsReverse = [...realChatItems].reverse() // Check from the end to find the latest pending item
    const itemToPoll = chatItemsReverse.find(
      (item) =>
        item.status === 'awaiting_start' || item.status === 'in_progress'
    )

    if (itemToPoll && itemToPoll.id && itemToPoll.id !== pollingChatId) {
      setPollingChatId(itemToPoll.id)
      console.log(
        `Setting pollingChatId to: ${itemToPoll.id} with status: ${itemToPoll.status}`
      )
    } else if (!itemToPoll && pollingChatId) {
      // If no real chat item needs polling (and no real items are awaiting/in_progress),
      // and we were previously polling, stop.
      setPollingChatId(null)
      console.log(
        'No real chat item needs polling, stopping individual polling.'
      )
    }
  }, [chatItems, pollingChatId]) // Depend on chatItems and pollingChatId

  // New useQuery for polling a single chat item
  useQuery({
    queryKey: getChatTranscriptionsTranscriptionIdChatChatIdGetQueryKey({
      path: { transcription_id: transcriptionId, chat_id: pollingChatId! },
    }),
    queryFn: async () => {
      // Direct API call using the client
      const response =
        await api.getChatTranscriptionsTranscriptionIdChatChatIdGet({
          path: { transcription_id: transcriptionId, chat_id: pollingChatId! },
        })
      return response.data
    },
    enabled: !!pollingChatId, // Only run when pollingChatId is set
    refetchInterval: (query) => {
      const currentStatus = query.state.data?.status as string | undefined
      // Continue polling while awaiting or in progress
      if (
        currentStatus === 'awaiting_start' ||
        currentStatus === 'in_progress'
      ) {
        console.log(
          `Polling individual chat: ${pollingChatId}, status: ${currentStatus}`
        )
        return 1000 // Poll every 1 second
      }

      // Stop polling on terminal states (completed/success/failed) or when status is defined and not pending
      if (currentStatus) {
        console.log(
          `Individual chat ${pollingChatId} polling finished with status: ${currentStatus}`
        )
        if (query.state.data) {
          const updatedItem = query.state.data as ChatGetResponse
          queryClient.setQueryData(
            listChatTranscriptionsTranscriptionIdChatGetQueryKey({
              path: { transcription_id: transcriptionId },
            }),
            (old: { chat?: ChatGetResponse[] } | undefined) => {
              const prevChat: ChatGetResponse[] =
                (old?.chat as ChatGetResponse[]) ?? []

              // Try to replace by id
              const idxById = prevChat.findIndex((c) => c.id === updatedItem.id)
              if (idxById !== -1) {
                const next = prevChat.slice()
                next[idxById] = updatedItem
                return { chat: next }
              }

              // If not found by id (e.g., we had an optimistic item), remove any optimistic placeholder
              // that matches the same user_content and is still pending, then append the real item.
              const filtered = prevChat.filter(
                (c) =>
                  !(
                    typeof c.id === 'string' &&
                    c.id.startsWith('optimistic-') &&
                    c.user_content === updatedItem.user_content
                  )
              )
              return { chat: [...filtered, updatedItem] }
            }
          )

          // Also ensure the list gets a fresh fetch in case other items changed on the server
          queryClient.invalidateQueries({
            queryKey: listChatTranscriptionsTranscriptionIdChatGetQueryKey({
              path: { transcription_id: transcriptionId },
            }),
          })
        }
        setPollingChatId(null) // Stop polling this ID
        return false // Stop refetching
      }

      // If we have no status yet, keep polling fast
      return 1000
    },
  })

  // Flatten for rendering as chat messages (user then assistant if present)
  const messages: Array<{ role: 'user' | 'assistant'; content: string }> =
    chatItems.flatMap((item) => {
      const m: Array<{ role: 'user' | 'assistant'; content: string }> = [
        { role: 'user' as const, content: item.user_content },
      ]
      if (item.assistant_content)
        m.push({ role: 'assistant' as const, content: item.assistant_content })
      return m
    })

  // Auto-scroll to bottom when chat updates
  useEffect(() => {
    listEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages.length])

  const { mutate: createChat, isPending: sending } = useMutation({
    ...createChatTranscriptionsTranscriptionIdChatPostMutation(),
  })

  const { mutate: clearChat, isPending: clearing } = useMutation({
    ...deleteChatsTranscriptionsTranscriptionIdChatDeleteMutation(),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: listChatTranscriptionsTranscriptionIdChatGetQueryKey({
          path: { transcription_id: transcriptionId },
        }),
      })
      setPollingChatId(null) // Clear any active polling when chat is cleared
    },
  })

  const handleSend = () => {
    const content = input.trim()
    if (!content || !transcriptionId) return

    // Optimistically add the user message to cache to improve UX
    queryClient.setQueryData(
      listChatTranscriptionsTranscriptionIdChatGetQueryKey({
        path: { transcription_id: transcriptionId },
      }),
      (old: { chat?: ChatGetResponse[] } | undefined) => {
        const prevChat: ChatGetResponse[] =
          (old?.chat as ChatGetResponse[]) ?? []
        const now = new Date().toISOString()
        const optimistic: ChatGetResponse = {
          id: `optimistic-${Date.now()}`, // Temporary ID
          created_datetime: now,
          updated_datetime: now,
          user_content: content,
          assistant_content: null,
          status: 'awaiting_start', // Mark as awaiting for immediate detection
        }
        return { chat: [...prevChat, optimistic] }
      }
    )

    createChat(
      {
        path: { transcription_id: transcriptionId },
        body: { user_content: content },
      },
      {
        onSuccess: () => {
          // Invalidate the main chat list query to force a refresh with the real data
          // This refresh will then trigger the useEffect to find the item to poll.
          queryClient.invalidateQueries({
            queryKey: listChatTranscriptionsTranscriptionIdChatGetQueryKey({
              path: { transcription_id: transcriptionId },
            }),
          })
        },
        onSettled: () => {
          setInput('')
        },
      }
    )
  }

  if (isLoading) {
    return (
      <div className="flex h-60 items-center justify-center text-slate-500">
        <Loader2 className="mr-2 animate-spin" /> Loading chat...
      </div>
    )
  }

  const waitingForAssistant = (() => {
    // If we are actively polling an individual chat item, it means the assistant is thinking.
    if (!!pollingChatId) return true
    // Otherwise, check the last item in the fetched chat list.
    if (chatItems.length === 0) return false
    const last = chatItems[chatItems.length - 1]
    return last.status === 'awaiting_start' || last.status === 'in_progress'
  })()

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-slate-600">
          <MessageCircle />
          <span className="text-sm">
            Use this chat interface to ask questions or extract information
            about the meeting. Note that the responses here will not modify your
            Meeting summary (use AI Edit under the Meeting summary tab for
            that).
          </span>
        </div>
        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button
              variant="outline"
              size="sm"
              disabled={messages.length === 0 || clearing}
              className="border-red-300 text-red-500 hover:border-red-400 hover:text-red-600"
            >
              {clearing ? (
                <Loader2 className="mr-2 animate-spin" />
              ) : (
                <Trash2 className="mr-2 h-4 w-4" />
              )}
              Clear History
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>
                Are you sure you want to clear your chat?
              </AlertDialogTitle>
              <AlertDialogDescription>
                Your chat history will be permenantly deleted.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction
                className="bg-red-600 hover:bg-red-800 active:bg-yellow-400"
                onClick={() =>
                  clearChat({
                    path: { transcription_id: transcriptionId },
                  })
                }
              >
                <Trash2 />
                Clear Chat
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>

      <div className="flex max-h-[60vh] flex-col gap-2 overflow-y-auto rounded border bg-white p-3">
        {messages.length === 0 ? (
          <div className="text-sm text-slate-500">
            Start the conversation by asking a question or asking for
            information about the meeting.
          </div>
        ) : (
          messages.map((msg, idx) => (
            <div
              key={idx}
              className={
                'inline-block w-full rounded px-3 py-2 ' +
                (msg.role === 'user' ? 'bg-blue-100' : '')
              }
            >
              <div className="prose max-w-none">
                <Markdown
                  components={{
                    // eslint-disable-next-line @typescript-eslint/no-unused-vars
                    a({ node, ...rest }) {
                      return (
                        <CitationContent
                          linkChildren={rest.children}
                          href={rest.href}
                          onCitationClick={handleCitationClick}
                        />
                      )
                    },
                  }}
                >
                  {renderMessageContent(msg.role, msg.content)}
                </Markdown>
              </div>
            </div>
          ))
        )}
        {waitingForAssistant && (
          <div className="text-left text-sm text-slate-500">
            <Loader2 className="mr-1 inline animate-spin" />
            Thinking...
          </div>
        )}
        <div ref={listEndRef} />
      </div>

      {citationPopover && (
        <CitationPopoverWrapper
          citationPopover={citationPopover}
          isPopoverOpen={isPopoverOpen}
          onOpenChange={(open) => {
            setIsPopoverOpen(open)
            if (!open) closeCitationPopover()
          }}
          transcription={transcription}
        />
      )}

      <div className="flex items-end gap-2">
        <Textarea
          placeholder="Ask anything..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault() // Prevent default behavior (e.g., newline in textarea)
              handleSend()
            }
          }}
        />
        <Button
          type="button"
          onClick={handleSend}
          disabled={!input.trim() || sending}
          className="bg-indigo-700 hover:bg-indigo-800"
        >
          {sending ? (
            <Loader2 className="mr-2 animate-spin" />
          ) : (
            <SendHorizontal className="mr-2" />
          )}
          Send
        </Button>
      </div>
    </div>
  )
}

export default ChatTab
