// This file defines a ChatInput component that provides a text input area for users to type messages and send them
// It includes a textarea for message input, a send button, and a file upload button
// The component handles input changes, form submission, and keyboard events for sending messages

import React, { useState, useRef, useEffect, KeyboardEvent } from 'react';
import { Send, X, FileText } from 'lucide-react';
import { FileUploadButton } from './FileUploadButton';

interface ChatInputProps {
  onSend: (message: string, file?: File | null) => void;
  disabled?: boolean;
  uploading?: boolean;
}

export const ChatInput: React.FC<ChatInputProps> = ({
  onSend,
  disabled,
  uploading,
}) => {
  const [input, setInput] = useState('');
  const [attachedFile, setAttachedFile] = useState<File | null>(null);
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
    const trimmedInput = input.trim();
    if (!trimmedInput && !attachedFile) return;
    if (disabled) return;
    onSend(trimmedInput, attachedFile);
    setInput('');
    setAttachedFile(null);
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="w-full flex flex-col bg-zinc-900 border border-zinc-800 rounded-3xl p-2 focus-within:border-zinc-700 transition-colors">
      {attachedFile && (
        <div className="flex items-center gap-2 px-3 py-1.5 bg-zinc-800/80 text-zinc-200 text-xs rounded-xl border border-zinc-700/60 w-fit mb-2 ml-2 animate-fade-in shrink-0 select-none">
          <FileText className="w-3.5 h-3.5 text-blue-400" />
          <span className="truncate max-w-[200px] font-medium">{attachedFile.name}</span>
          <button
            type="button"
            onClick={() => setAttachedFile(null)}
            className="text-zinc-400 hover:text-zinc-100 focus:outline-none transition-colors p-0.5 rounded hover:bg-zinc-700"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      <form
        onSubmit={handleSubmit}
        className="relative flex items-end gap-2 w-full"
      >
        <FileUploadButton
          onFileSelect={setAttachedFile}
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
          disabled={disabled || (!input.trim() && !attachedFile)}
          className="p-3 bg-blue-600 hover:bg-blue-700 disabled:bg-zinc-800 disabled:text-zinc-600 text-white rounded-full transition-colors flex items-center justify-center shrink-0 cursor-pointer"
        >
          <Send className="w-4 h-4" />
        </button>
      </form>
    </div>
  );
};
