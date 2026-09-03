// This file defines a MessageBubble component that renders individual chat messages in a chat interface
// It displays the message content, role (user or assistant), and applies different styles based on the sender

import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import clsx from 'clsx';
import { Message } from '@/types/chat';

interface MessageBubbleProps {
  message: Message;
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({ message }) => {
  const isUser = message.role === 'user';

  return (
    <div
      className={clsx(
        'flex w-full gap-4 py-6 px-4 md:px-6 rounded-2xl transition-colors',
        isUser ? 'bg-transparent' : 'bg-zinc-900/40 border border-zinc-850/20'
      )}
    >
      {/* Avatar */}
      <div
        className={clsx(
          'w-8 h-8 rounded-full flex items-center justify-center font-bold text-xs shrink-0 select-none',
          isUser
            ? 'bg-blue-600 text-white'
            : 'bg-zinc-800 text-blue-400 border border-zinc-700'
        )}
      >
        {isUser ? 'U' : 'AI'}
      </div>

      {/* Message content */}
      <div className="flex-1 min-w-0 prose prose-invert prose-sm md:prose-base max-w-none text-zinc-200">
        {isUser ? (
          <p className="whitespace-pre-wrap leading-relaxed">{message.content}</p>
        ) : message.content === '' ? (
          <div className="flex items-center gap-1.5 py-1">
            <span className="w-2.5 h-2.5 bg-blue-500 rounded-full animate-bounce delay-100" />
            <span className="w-2.5 h-2.5 bg-blue-500 rounded-full animate-bounce delay-200" />
            <span className="w-2.5 h-2.5 bg-blue-500 rounded-full animate-bounce delay-300" />
          </div>
        ) : (
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            className="markdown-content space-y-4 leading-relaxed"
            components={{
              pre({ node, ...props }) {
                return (
                  <div className="relative my-4 overflow-x-auto rounded-xl border border-zinc-800 bg-zinc-950 p-4 font-mono text-xs text-zinc-300">
                    <pre {...props} />
                  </div>
                );
              },
              code({ node, className, ...props }) {
                const isInline = !className;
                return isInline ? (
                  <code className="rounded bg-zinc-800 px-1.5 py-0.5 font-mono text-xs text-blue-300" {...props} />
                ) : (
                  <code className={className} {...props} />
                );
              },
              table({ node, ...props }) {
                return (
                  <div className="my-4 overflow-x-auto rounded-xl border border-zinc-800">
                    <table className="min-w-full divide-y divide-zinc-800 text-left text-sm" {...props} />
                  </div>
                );
              },
              th({ node, ...props }) {
                return <th className="bg-zinc-900 px-4 py-2 font-medium text-zinc-200" {...props} />;
              },
              td({ node, ...props }) {
                return <td className="border-t border-zinc-800 px-4 py-2 text-zinc-400" {...props} />;
              },
              a({ node, ...props }) {
                return <a className="text-blue-400 hover:underline" target="_blank" rel="noopener noreferrer" {...props} />;
              }
            }}
          >
            {message.content}
          </ReactMarkdown>
        )}
      </div>
    </div>
  );
};
