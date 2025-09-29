'use client'

import React, { useState } from 'react'
import { Thread } from "@/components/assistant-ui/thread";
import { AssistantRuntimeProvider, ThreadHistoryAdapter } from '@assistant-ui/react';
import { useParams } from 'next/navigation';
import { ChatWithConversationIDAPIRuntime, LoadConversationHistory } from '@/lib/integration/client/chat-conversation';

function ChatPage() {
  const params = useParams()
  const conversationId = params.conversationId as string
  const [isLoadingHistory, setIsLoadingHistory] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const HistoryAdapter: ThreadHistoryAdapter = {

    async load() {
      try {
        if (!conversationId) {
          return { messages: [] };
        }

        setIsLoadingHistory(true)
        setError(null)

        const historyData = await LoadConversationHistory(conversationId);

        if (historyData === null) {
          setError('Failed to load conversation history')
          setIsLoadingHistory(false)
          return { messages: [] };
        }

        if (historyData.length === 0) {
          setError('Conversation not found')
          setIsLoadingHistory(false)
          return { messages: [] };
        }

        setIsLoadingHistory(false)
        return { messages: historyData };
      } catch (error) {
        console.error('Failed to load conversation history:', error);
        setError('Failed to load conversation history')
        setIsLoadingHistory(false)
        return { messages: [] };
      }
    },

    async append() {
      // The message will be saved automatically by your backend when streaming completes
      // You might want to implement this if you need to save messages immediately
    },
  }

  const runtime = ChatWithConversationIDAPIRuntime(conversationId, HistoryAdapter)

  return (
    <AssistantRuntimeProvider runtime={runtime}>
      <div className='h-screen pt-16 md:pt-0'>
        {error ? (
          // Show error state if conversation failed to load
          <div className="h-full flex items-center justify-center">
            <div className="text-center space-y-4 max-w-md">
              <div className="text-red-500 text-2xl">😕</div>
              <h2 className="text-xl font-semibold text-gray-800">Oops!</h2>
              <p className="text-gray-600">{error}</p>
              <button
                onClick={() => window.location.reload()}
                className="px-4 py-2 bg-primary/85 hover:bg-primary text-white rounded-lg transition-colors"
              >
                Try Again
              </button>
            </div>
          </div>
        ) : (
          // Show main chat interface with loading skeleton when needed
          <Thread isLoading={isLoadingHistory} />
        )}
      </div>
    </AssistantRuntimeProvider>
  )
}

export default ChatPage