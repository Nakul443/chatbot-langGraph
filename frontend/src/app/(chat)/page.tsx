// This file defines the Home component, which serves as the landing page for the chat application.
// It provides a greeting message, an input area for starting new chats, and handles file uploads.
// The component uses Zustand stores for managing chat state and authentication state, and it interacts with the backend API for file uploads and chat streaming.

'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { ChatInput } from '@/components/chat/ChatInput';
import { useChatStream } from '@/hooks/useChatStream';
import { useChatStore } from '@/store/authStore';
import { Sparkles, MessageSquare } from 'lucide-react';
import { apiService } from '@/services/api';

interface PageProps {
  refetchThreads?: () => void;
}

export default function Home({ refetchThreads }: PageProps) {
  const router = useRouter();
  const { streamChat } = useChatStream();
  const { setActiveThreadId, isStreaming } = useChatStore();
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleNewChat = async (message: string) => {
    // Generate unique random thread ID for new conversation
    const newThreadId = `thread_${Math.random().toString(36).substring(2, 15)}`;
    setActiveThreadId(newThreadId);
    
    // Redirect to active thread immediately
    router.push(`/${newThreadId}`);

    // Wait short period for path update before streaming
    setTimeout(async () => {
      await streamChat(message, newThreadId);
      if (refetchThreads) refetchThreads();
    }, 100);
  };

  const handleFileUpload = async (file: File) => {
    setUploading(true);
    setError(null);
    try {
      const newThreadId = `thread_${Math.random().toString(36).substring(2, 15)}`;
      setActiveThreadId(newThreadId);
      router.push(`/${newThreadId}`);

      // Wait short period for path update before upload & initial stream
      setTimeout(async () => {
        await apiService.uploadFile(file, newThreadId);
        await streamChat(`I've uploaded the file: ${file.name} - please summarize it or answer questions based on it.`, newThreadId);
        if (refetchThreads) refetchThreads();
      }, 100);
    } catch (err: any) {
      setError(err.message || 'File upload failed');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col justify-between h-full bg-zinc-950">
      {/* Centered Empty State Greeting */}
      <div className="flex-1 flex flex-col items-center justify-center p-4 text-center max-w-2xl mx-auto space-y-6">
        <div className="p-4 rounded-3xl bg-blue-600/10 text-blue-400 border border-blue-500/15 shadow-2xl animate-pulse">
          <Sparkles className="w-10 h-10" />
        </div>
        <div className="space-y-2">
          <h1 className="text-3xl md:text-4xl font-bold bg-gradient-to-r from-zinc-100 via-zinc-200 to-zinc-400 bg-clip-text text-transparent">
            Hello! How can I help you today?
          </h1>
          <p className="text-zinc-500 text-sm md:text-base max-w-md mx-auto">
            Ask complex queries, upload PDF documents for intelligent ingestion, or search web networks live.
          </p>
        </div>

        {error && (
          <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-xl text-xs text-red-400 max-w-md">
            {error}
          </div>
        )}
      </div>

      {/* Centered Input Column */}
      <div className="w-full max-w-3xl mx-auto px-4 md:px-6 pb-8">
        <ChatInput
          onSend={handleNewChat}
          onFileUpload={handleFileUpload}
          disabled={isStreaming}
          uploading={uploading}
        />
        <p className="text-center text-[10px] text-zinc-600 mt-3 select-none">
          Our LangGraph Agent may display inaccurate facts. Please verify important details.
        </p>
      </div>
    </div>
  );
}
