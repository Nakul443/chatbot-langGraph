// This file defines a ThreadListItem component that represents an individual thread in a list of threads
// It displays the thread's preview, last updated time, and indicates if it is the active thread
// The component handles click events to select a thread and can be rendered in a collapsed state

// the purpose of this file is to provide a reusable component for displaying threads in a sidebar or list,
// allowing users to easily navigate between different chat threads

import React from 'react';
import { MessageSquare } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import clsx from 'clsx';
import { Thread } from '@/types/chat';

interface ThreadListItemProps {
  thread: Thread;
  active: boolean;
  onClick: () => void;
  collapsed?: boolean;
}

export const ThreadListItem: React.FC<ThreadListItemProps> = ({
  thread,
  active,
  onClick,
  collapsed,
}) => {
  // Try parsing date comfortably
  let formattedTime = '';
  try {
    if (thread.updated_at) {
      formattedTime = formatDistanceToNow(new Date(thread.updated_at), { addSuffix: true });
    }
  } catch {
    formattedTime = 'recently';
  }

  // derive pretty clean display preview title from the raw thread structure
  const displayTitle = thread.preview || `Thread: ${thread.thread_id.substring(0, 8)}`;

  return (
    <button
      onClick={onClick}
      className={clsx(
        'flex items-center gap-3 w-full px-4 py-3 rounded-xl text-left transition-all group relative',
        active
          ? 'bg-zinc-800 text-zinc-100 font-medium'
          : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-850'
      )}
      title={displayTitle}
    >
      <MessageSquare className={clsx('w-4 h-4 shrink-0', active ? 'text-blue-400' : 'text-zinc-500')} />
      {!collapsed && (
        <div className="flex-1 min-w-0">
          <p className="text-sm truncate leading-snug">{displayTitle}</p>
          <span className="text-[10px] text-zinc-500 mt-0.5 block">{formattedTime}</span>
        </div>
      )}
    </button>
  );
};
