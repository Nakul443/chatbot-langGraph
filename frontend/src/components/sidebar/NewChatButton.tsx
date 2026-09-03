// This file defines a NewChatButton component that renders a button for starting a new chat

import React from 'react';
import { Plus } from 'lucide-react';

interface NewChatButtonProps {
  onClick: () => void;
  collapsed?: boolean;
}

export const NewChatButton: React.FC<NewChatButtonProps> = ({ onClick, collapsed }) => {
  return (
    <button
      onClick={onClick}
      className="flex items-center gap-3 w-full px-4 py-3 bg-zinc-800 hover:bg-zinc-750 border border-zinc-700/60 hover:border-zinc-650 text-zinc-100 rounded-2xl transition-all font-medium text-sm shadow-sm hover:shadow active:scale-[0.98]"
    >
      <Plus className="w-4 h-4 text-blue-400 shrink-0" />
      {!collapsed && <span className="truncate">New chat</span>}
    </button>
  );
};
