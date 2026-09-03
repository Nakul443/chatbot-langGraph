// file to define types for chat messages, threads, and user authentication state
// This file is used in the frontend to ensure type safety when working with chat-related data

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at?: string;
}

export interface Thread {
  thread_id: string;
  updated_at: string;
  preview?: string;
}

export interface User {
  id: string;
  email: string;
}

export interface AuthState {
  token: string | null;
  user: User | null;
}
