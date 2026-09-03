// This file defines the Zustand stores for managing authentication and chat state in the application
// The AuthStore manages user authentication state, including the current user and auth token
// The ChatStore manages the state of the chat interface, including active thread, messages, and streaming status

// it stores the authentication state of the user, including the current user and their auth token
// this can be used across the application to determine if a user is logged in and to access their information

import { create } from 'zustand';
import { User, Message } from '@/types/chat';


interface AuthStore {
  user: User | null;
  token: string | null;
  setAuth: (user: User | null, token: string | null) => void;
  clearAuth: () => void;
}

// AuthStore manages user's login state across the application
export const useAuthStore = create<AuthStore>((set) => ({
  user: null,
  token: null,
  setAuth: (user, token) => set({ user, token }),
  clearAuth: () => set({ user: null, token: null }),
}));

interface ChatStore {
  activeThreadId: string | null;
  messages: Message[];
  isStreaming: boolean;
  setActiveThreadId: (threadId: string | null) => void;
  setMessages: (messages: Message[] | ((prev: Message[]) => Message[])) => void;
  addMessage: (message: Message) => void;
  updateLastMessage: (content: string) => void;
  setIsStreaming: (isStreaming: boolean) => void;
}

// Manages the real-time chat interface, message history, and UI states during conversations
export const useChatStore = create<ChatStore>((set) => ({
  activeThreadId: null,
  messages: [],
  isStreaming: false,
  setActiveThreadId: (threadId) => set({ activeThreadId: threadId }),
  setMessages: (messages) => set((state) => ({
    messages: typeof messages === 'function' ? messages(state.messages) : messages
  })),
  addMessage: (message) => set((state) => ({ messages: [...state.messages, message] })),
  updateLastMessage: (content) => set((state) => {
    if (state.messages.length === 0) return {};
    const newMessages = [...state.messages];
    newMessages[newMessages.length - 1] = {
      ...newMessages[newMessages.length - 1],
      content: newMessages[newMessages.length - 1].content + content,
    };
    return { messages: newMessages };
  }),
  setIsStreaming: (isStreaming) => set({ isStreaming }),
}));
