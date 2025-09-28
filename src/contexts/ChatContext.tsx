'use client'

import { createContext, useContext, useState, ReactNode, useEffect } from 'react'
import { formatRelativeTime } from '@/utils/date-utils'
import { useSession } from 'next-auth/react'
import { DeleteConversation, GetConversationsList, TogglePinConversation } from '@/lib/integration/client/chat-conversation'

interface ChatItem {
  id: string
  title: string
  date: string
  createdAt: number // epoch milliseconds
  isPinned: boolean
}


interface ChatContextType {
  chatHistory: ChatItem[]
  setChatHistory: (history: ChatItem[]) => void
  getGroupedChatHistory: () => GroupedChatHistory
  togglePinChat: (chatId: string) => Promise<void>
  deleteChat: (chatId: string) => Promise<void>
  loadConversations: () => Promise<void>
  isLoading: boolean
  isInitialLoading: boolean
  error: string | null
}

interface GroupedChatHistory {
  pinned: ChatItem[]
  today: ChatItem[]
  yesterday: ChatItem[]
  previous7Days: ChatItem[]
  previous30Days: ChatItem[]
  older: ChatItem[]
}

// Utility function to group chats by date
function groupChatsByDate(chats: ChatItem[]): GroupedChatHistory {
  const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const yesterday = new Date(today.getTime() - 24 * 60 * 60 * 1000)
  const sevenDaysAgo = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000)
  const thirtyDaysAgo = new Date(today.getTime() - 30 * 24 * 60 * 60 * 1000)

  const grouped: GroupedChatHistory = {
    pinned: [],
    today: [],
    yesterday: [],
    previous7Days: [],
    previous30Days: [],
    older: []
  }

  chats.forEach(chat => {
    if (chat.isPinned) {
      grouped.pinned.push(chat)
      return // Skip date-based grouping for pinned chats
    }

    const chatDate = new Date(chat.createdAt)
    const chatDateOnly = new Date(chatDate.getFullYear(), chatDate.getMonth(), chatDate.getDate())

    if (chatDateOnly.getTime() === today.getTime()) {
      grouped.today.push(chat)
    } else if (chatDateOnly.getTime() === yesterday.getTime()) {
      grouped.yesterday.push(chat)
    } else if (chatDateOnly >= sevenDaysAgo) {
      grouped.previous7Days.push(chat)
    } else if (chatDateOnly >= thirtyDaysAgo) {
      grouped.previous30Days.push(chat)
    } else {
      grouped.older.push(chat)
    }
  })

  // Sort each group by creation date (newest first)
  Object.values(grouped).forEach(group => {
    group.sort((a: ChatItem, b: ChatItem) => b.createdAt - a.createdAt)
  })

  return grouped
}

const ChatContext = createContext<ChatContextType | undefined>(undefined)

export function useChat() {
  const context = useContext(ChatContext)
  if (!context) {
    throw new Error('useChat must be used within a ChatProvider')
  }
  return context
}

interface ChatProviderProps {
  children: ReactNode
}

const now = new Date()
const MockChatHistory: ChatItem[] = [
    {
      id: '1',
      title: 'How to build a web application',
      date: formatRelativeTime(now.getTime() - 2 * 60 * 60 * 1000),
      createdAt: now.getTime() - 2 * 60 * 60 * 1000, // 2 hours ago
      isPinned: true
    },
    {
      id: '2',
      title: 'React best practices',
      date: formatRelativeTime(now.getTime() - 1 * 24 * 60 * 60 * 1000),
      createdAt: now.getTime() - 1 * 24 * 60 * 60 * 1000, // 1 day ago
      isPinned: false
    },
    {
      id: '3',
      title: 'TypeScript basics',
      date: formatRelativeTime(now.getTime() - 3 * 24 * 60 * 60 * 1000),
      createdAt: now.getTime() - 3 * 24 * 60 * 60 * 1000, // 3 days ago
      isPinned: true
    },
    {
      id: '4',
      title: 'Next.js routing',
      date: formatRelativeTime(now.getTime() - 7 * 24 * 60 * 60 * 1000),
      createdAt: now.getTime() - 7 * 24 * 60 * 60 * 1000, // 1 week ago
      isPinned: false
    },
    {
      id: '5',
      title: 'CSS Grid vs Flexbox',
      date: formatRelativeTime(now.getTime() - 14 * 24 * 60 * 60 * 1000),
      createdAt: now.getTime() - 14 * 24 * 60 * 60 * 1000, // 2 weeks ago
      isPinned: false
    },
    {
      id: '6',
      title: 'Database design principles',
      date: formatRelativeTime(now.getTime() - 21 * 24 * 60 * 60 * 1000),
      createdAt: now.getTime() - 21 * 24 * 60 * 60 * 1000, // 3 weeks ago
      isPinned: false
    },
    {
      id: '7',
      title: 'API authentication methods',
      date: formatRelativeTime(now.getTime() - 30 * 24 * 60 * 60 * 1000),
      createdAt: now.getTime() - 30 * 24 * 60 * 60 * 1000, // 1 month ago
      isPinned: false
    },
    {
      id: '8',
      title: 'Performance optimization techniques',
      date: formatRelativeTime(now.getTime() - 35 * 24 * 60 * 60 * 1000),
      createdAt: now.getTime() - 35 * 24 * 60 * 60 * 1000, // 35 days ago
      isPinned: false
    },
    {
      id: '9',
      title: 'Testing strategies for React apps',
      date: formatRelativeTime(now.getTime() - 60 * 24 * 60 * 60 * 1000),
      createdAt: now.getTime() - 60 * 24 * 60 * 60 * 1000, // 2 months ago
      isPinned: false
    },
    {
      id: '10',
      title: 'Deployment best practices',
      date: formatRelativeTime(now.getTime() - 65 * 24 * 60 * 60 * 1000),
      createdAt: now.getTime() - 65 * 24 * 60 * 60 * 1000, // 65 days ago
      isPinned: false
    },
    {
      id: '11',
      title: 'State management solutions',
      date: formatRelativeTime(now.getTime() - 90 * 24 * 60 * 60 * 1000),
      createdAt: now.getTime() - 90 * 24 * 60 * 60 * 1000, // 3 months ago
      isPinned: false
    },
    {
      id: '12',
      title: 'Component design patterns',
      date: formatRelativeTime(now.getTime() - 95 * 24 * 60 * 60 * 1000),
      createdAt: now.getTime() - 95 * 24 * 60 * 60 * 1000, // 95 days ago
      isPinned: false
    },
    {
      id: '13',
      title: 'Error handling in JavaScript',
      date: formatRelativeTime(now.getTime() - 120 * 24 * 60 * 60 * 1000),
      createdAt: now.getTime() - 120 * 24 * 60 * 60 * 1000, // 4 months ago
      isPinned: false
    },
    {
      id: '14',
      title: 'Web security fundamentals',
      date: formatRelativeTime(now.getTime() - 125 * 24 * 60 * 60 * 1000),
      createdAt: now.getTime() - 125 * 24 * 60 * 60 * 1000, // 125 days ago
      isPinned: false
    },
    {
      id: '15',
      title: 'Progressive Web Apps',
      date: formatRelativeTime(now.getTime() - 150 * 24 * 60 * 60 * 1000),
      createdAt: now.getTime() - 150 * 24 * 60 * 60 * 1000, // 5 months ago
      isPinned: false
    },
  ]

export function ChatProvider({ children }: ChatProviderProps) {
  const [chatHistory, setChatHistory] = useState<ChatItem[]>([])
  const { status } = useSession()

  const [isLoading, setIsLoading] = useState(false)
  const [isInitialLoading, setIsInitialLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Load conversations on mount
  useEffect(() => {
    if (status == 'authenticated') {

      loadConversations()
      const autoUpdate = setInterval(() => {
        
        loadConversations()
      }, 20 * 1000); // Refresh every 20 seconds
      
      return () => {
        clearInterval(autoUpdate)
      }
    }

    return () => {}

  }, [status])

  const loadConversations = async () => {
    try {
      setIsLoading(true)
      setError(null)

      const data = await GetConversationsList()
      if (data === null) {
        setError('Failed to load conversations')
        return
      }

      setChatHistory([...data])
    } catch (err) {
      setError('Failed to load conversations')
      console.error('Load conversations error:', err)
    } finally {
      setIsLoading(false)
      setIsInitialLoading(false) // Set initial loading to false after first load attempt
    }
  }

  const togglePinChat = async (chatId: string) => {
    try {
      setError(null)
      const response = await TogglePinConversation(chatId)
      if (!response) {
        throw new Error('Failed to toggle pin status')
      }
      // Update local state optimistically
      setChatHistory(prevHistory =>
        prevHistory.map(chat =>
          chat.id === chatId
            ? { ...chat, isPinned: !chat.isPinned }
            : chat
        )
      )
    } catch (err) {
      setError('Failed to toggle pin status')
      console.error('Toggle pin error:', err)
    }
  }

  const deleteChat = async (chatId: string) => {
    try {
      setError(null)
      const response = await DeleteConversation(chatId)
      if (!response) {
        throw new Error('Failed to delete conversation')
      }
      // Update local state optimistically
      setChatHistory(prevHistory =>
        prevHistory.filter(chat => chat.id !== chatId)
      )
    } catch (err) {
      setError('Failed to delete conversation')
      console.error('Delete conversation error:', err)
    }
  }

  const getGroupedChatHistory = () => groupChatsByDate(chatHistory)

  return (
    <ChatContext.Provider value={{
      chatHistory,
      setChatHistory,
      getGroupedChatHistory,
      togglePinChat,
      deleteChat,
      loadConversations,
      isLoading,
      isInitialLoading,
      error
    }}>
      {children}
    </ChatContext.Provider>
  )
}