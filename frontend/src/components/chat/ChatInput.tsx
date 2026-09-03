// This file defines a ChatInput component that provides a text input area for users to type messages and send them
// It includes a textarea for message input, a send button, and a file upload button
// The component handles input changes, form submission, and keyboard events for sending messages

import React, { useState, useRef, useEffect, KeyboardEvent } from 'react';
import { Send } from 'lucide-react';
import { FileUploadButton } from './FileUploadButton';

interface ChatInputProps {
  onSend: (message: string) => void;
  onFileUpload: (file: File) => void;
  disabled?: boolean;
  uploading?: boolean;
}

export const ChatInput: React.FC<ChatInputProps> = ({
  onSend,
  onFileUpload,
  disabled,
  uploading,
}) => {
  const [input, setInput] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    // Auto-resize textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [input]);

  const handleSubmit = (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!input.trim() || disabled) return;
    onSend(input);
    setInput('');
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="relative flex items-end gap-2 w-full bg-zinc-900 border border-zinc-800 rounded-3xl p-2 focus-within:border-zinc-700 transition-colors"
    >
      <FileUploadButton
        onFileSelect={onFileUpload}
        disabled={disabled}
        uploading={uploading}
      />

      <textarea
        ref={textareaRef}
        rows={1}
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask anything..."
        className="flex-1 max-h-[200px] bg-transparent text-zinc-100 placeholder-zinc-500 py-3 px-2 text-sm focus:outline-none resize-none leading-relaxed"
        disabled={disabled}
      />

      <button
        type="submit"
        disabled={disabled || !input.trim()}
        className="p-3 bg-blue-600 hover:bg-blue-700 disabled:bg-zinc-800 disabled:text-zinc-600 text-white rounded-full transition-colors flex items-center justify-center shrink-0 cursor-pointer"
      >
        <Send className="w-4 h-4" />
      </button>
    </form>
  );
};
