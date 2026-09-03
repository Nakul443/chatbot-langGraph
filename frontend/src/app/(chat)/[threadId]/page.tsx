// This file defines the ThreadPage component, which represents a chat thread page in the application.
// It handles fetching message history, streaming new messages, and managing the chat input and file uploads.
// The component uses Zustand stores for managing chat state and authentication state.

'use client';

import React, { useEffect, useRef, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { MessageBubble } from '@/components/chat/MessageBubble';
import { ChatInput } from '@/components/chat/ChatInput';
import { useChatStream } from '@/hooks/useChatStream';
import { useChatStore } from '@/store/authStore';
import { apiService } from '@/services/api';
import { Sparkles } from 'lucide-react';

interface PageProps {
  refetchThreads?: () => void;
}

export default function ThreadPage({ refetchThreads }: PageProps) {
  const params = useParams();
  const router = useRouter();
  const threadId = params.threadId as string;

  const { messages, setMessages, activeThreadId, setActiveThreadId, isStreaming } = useChatStore();
  const { streamChat } = useChatStream();
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto scroll to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Handle direct navigation or deep link thread synchronization
  useEffect(() => {
    if (threadId && activeThreadId !== threadId) {
      setActiveThreadId(threadId);
      apiService.getHistory(threadId)
        .then((history) => {
          if (Array.isArray(history)) {
            const mapped = history.map((msg: any) => ({
              id: msg.id || Math.random().toString(),
              role: msg.role === 'user' ? 'user' : 'assistant',
              content: msg.content || '',
            }));
            setMessages(mapped);
          } else {
            setMessages([]);
          }
        })
        .catch((err) => {
          console.error('Failed to restore history', err);
          setMessages([]);
        });
    }
  }, [threadId, activeThreadId, setActiveThreadId, setMessages]);

  const handleSend = async (message: string) => {
    if (!threadId) return;
    await streamChat(message, threadId);
    if (refetchThreads) refetchThreads();
  };

  const handleFileUpload = async (file: File) => {
    if (!threadId) return;
    setUploading(true);
    setError(null);
    try {
      await apiService.uploadFile(file, threadId);
      // Automatically prompt graph to index uploaded file
      await streamChat(`I've uploaded the file: ${file.name} - please summarize it or answer questions based on it.`, threadId);
      if (refetchThreads) refetchThreads();
    } catch (err: any) {
      setError(err.message || 'File upload failed');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-zinc-950">
      {/* Top Header */}
      <div className="h-14 px-6 border-b border-zinc-900/60 flex items-center bg-zinc-950 select-none shrink-0">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
          <p className="text-xs font-semibold text-zinc-300 uppercase tracking-widest">
            Active Workspace
          </p>
        </div>
      </div>

      {/* Messages body */}
      <div className="flex-1 overflow-y-auto px-4 py-6 md:px-0">
        <div className="max-w-3xl mx-auto space-y-2">
          {messages.map((message) => (
            <MessageBubble key={message.id} message={message} />
          ))}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Footer warning + input dock */}
      <div className="w-full max-w-3xl mx-auto px-4 md:px-6 pb-8 shrink-0">
        {error && (
          <div className="mb-4 p-4 bg-red-500/10 border border-red-500/20 rounded-xl text-xs text-red-400">
            {error}
          </div>
        )}
        <ChatInput
          onSend={handleSend}
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
