// This file defines the ChatLayout component, which serves as the main layout for the chat application.
// It includes the Sidebar component for displaying chat threads and a main content area for rendering the active chat thread.
// The layout manages the state of the active thread, message history, and user authentication using Zustand stores.
// It also handles fetching message history from the backend API when a thread is selected.

'use client';

import React, { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Sidebar from '@/components/sidebar/Sidebar';
import { useThreads } from '@/hooks/useThreads';
import { useChatStore, useAuthStore } from '@/store/authStore';
import { apiService } from '@/services/api';

interface HistoryMessage {
  id?: string;
  role?: string;
  content?: string;
}

export default function ChatLayout({ children }: { children: React.ReactNode }) {
  const { threads, loading, refetch } = useThreads();
  const { activeThreadId, setActiveThreadId, setMessages } = useChatStore();
  const { setAuth } = useAuthStore();
  const router = useRouter();

  // On initial load, try fetching a temporary user detail if needed (or authStore hydrates if persist)
  useEffect(() => {
    // Populate simple mock/derived user state if empty from cookie context
    setAuth({ id: 'user', email: 'user@example.com' }, 'auth_token');
  }, [setAuth]);

  const handleThreadSelect = async (threadId: string | null) => {
    setActiveThreadId(threadId);
    if (threadId) {
      router.push(`/${threadId}`);
      try {
        const history = await apiService.getHistory(threadId);
        // Map backend history nodes into state Messages
        if (Array.isArray(history)) {
          const mapped = (history as HistoryMessage[]).map((msg) => ({
            id: msg.id || Math.random().toString(),
            role: msg.role === 'user' ? 'user' : 'assistant' as const,
            content: msg.content || '',
          }));
          setMessages(mapped);
        } else {
          setMessages([]);
        }
      } catch (err) {
        console.error('Failed to load thread history', err);
        setMessages([]);
      }
    } else {
      setMessages([]);
      router.push('/');
    }
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-zinc-950 text-zinc-100">
      <Sidebar
        threads={threads}
        activeThreadId={activeThreadId}
        onThreadSelect={handleThreadSelect}
        loading={loading}
      />
      <main className="flex-1 flex flex-col min-w-0 h-full relative">
        {React.cloneElement(children as React.ReactElement, { refetchThreads: refetch })}
      </main>
    </div>
  );
}
