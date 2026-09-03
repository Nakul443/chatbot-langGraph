import React, { useState } from 'react';
import { Menu, Settings, History, ChevronLeft, ChevronRight, MessageSquareCode } from 'lucide-react';
import clsx from 'clsx';
import { NewChatButton } from './NewChatButton';
import { ThreadListItem } from './ThreadListItem';
import { SettingsModal } from '../settings/SettingsModal';
import { Thread } from '@/types/chat';

interface SidebarProps {
  threads: Thread[];
  activeThreadId: string | null;
  onThreadSelect: (threadId: string | null) => void;
  loading?: boolean;
}

export const Sidebar: React.FC<SidebarProps> = ({
  threads,
  activeThreadId,
  onThreadSelect,
  loading,
}) => {
  const [collapsed, setCollapsed] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);

  return (
    <>
      <div
        className={clsx(
          'flex flex-col h-full bg-zinc-950 border-r border-zinc-900 transition-all duration-300 relative shrink-0',
          collapsed ? 'w-20' : 'w-72'
        )}
      >
        {/* Header toolbar */}
        <div className="flex items-center justify-between p-4 border-b border-zinc-900/60">
          {!collapsed && (
            <div className="flex items-center gap-2 font-semibold text-zinc-100 text-sm">
              <div className="p-1.5 rounded-lg bg-blue-600/10 text-blue-400 border border-blue-500/15">
                <MessageSquareCode className="w-5 h-5" />
              </div>
              <span>LangGraph Agent</span>
            </div>
          )}
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="p-2 rounded-lg text-zinc-400 hover:text-zinc-100 hover:bg-zinc-900 transition-colors cursor-pointer"
          >
            {collapsed ? <ChevronRight className="w-5 h-5" /> : <ChevronLeft className="w-5 h-5" />}
          </button>
        </div>

        {/* Action Button */}
        <div className="p-4">
          <NewChatButton onClick={() => onThreadSelect(null)} collapsed={collapsed} />
        </div>

        {/* Thread histories */}
        <div className="flex-1 overflow-y-auto px-2 space-y-1 scrollbar-thin">
          {!collapsed && (
            <p className="px-3 py-2 text-[10px] font-semibold text-zinc-500 uppercase tracking-wider flex items-center gap-1.5 select-none">
              <History className="w-3.5 h-3.5" />
              Recent Chats
            </p>
          )}

          {loading && threads.length === 0 ? (
            <div className="flex justify-center p-8">
              <span className="w-5 h-5 border-2 border-zinc-700 border-t-blue-500 rounded-full animate-spin" />
            </div>
          ) : threads.length === 0 ? (
            <div className="p-4 text-center text-xs text-zinc-600 font-medium">
              {!collapsed && 'No recent chats'}
            </div>
          ) : (
            threads.map((thread) => (
              <ThreadListItem
                key={thread.thread_id}
                thread={thread}
                active={activeThreadId === thread.thread_id}
                onClick={() => onThreadSelect(thread.thread_id)}
                collapsed={collapsed}
              />
            ))
          )}
        </div>

        {/* Bottom Panel Controls */}
        <div className="p-4 border-t border-zinc-900">
          <button
            onClick={() => setSettingsOpen(true)}
            className="flex items-center gap-3 w-full p-3 rounded-xl hover:bg-zinc-900 text-zinc-400 hover:text-zinc-100 transition-all font-medium text-sm cursor-pointer"
          >
            <Settings className="w-4 h-4 shrink-0" />
            {!collapsed && <span className="truncate">Settings</span>}
          </button>
        </div>
      </div>

      <SettingsModal isOpen={settingsOpen} onClose={() => setSettingsOpen(false)} />
    </>
  );
};
export default Sidebar;
