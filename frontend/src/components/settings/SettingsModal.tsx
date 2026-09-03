// This file defines a SettingsModal component that displays user account information and settings in a modal dialog

import React from 'react';
import { LogOut, User as UserIcon } from 'lucide-react';
import { Modal } from '../ui/Modal';
import { Button } from '../ui';
import { useAuth } from '@/hooks/useAuth';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({ isOpen, onClose }) => {
  const { user, logout, loading } = useAuth();

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Account & Settings">
      <div className="space-y-6">
        {/* User profile segment */}
        <div className="flex items-center gap-4 p-4 rounded-xl bg-zinc-850/50 border border-zinc-800">
          <div className="w-12 h-12 rounded-full bg-blue-600/25 flex items-center justify-center text-blue-400 border border-blue-500/30">
            <UserIcon className="w-6 h-6" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-zinc-100 truncate">{user?.email || 'User Account'}</p>
            <p className="text-xs text-zinc-500">Standard User</p>
          </div>
        </div>

        {/* Info segment */}
        <div className="text-xs text-zinc-500 bg-zinc-950/20 p-4 rounded-xl border border-zinc-850/30 leading-relaxed space-y-1">
          <p>Connected Environment: LangGraph MCP Network</p>
          <p>Checkpointer Engine: PostgreSQL Active Instance</p>
        </div>

        {/* Action triggers */}
        <div className="flex justify-end pt-2 border-t border-zinc-850">
          <Button
            variant="danger"
            size="sm"
            onClick={async () => {
              await logout();
              onClose();
            }}
            loading={loading}
          >
            <LogOut className="w-4 h-4 mr-2" />
            Sign Out
          </Button>
        </div>
      </div>
    </Modal>
  );
};
