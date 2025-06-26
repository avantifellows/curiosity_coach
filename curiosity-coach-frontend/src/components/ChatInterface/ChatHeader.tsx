import React from 'react';
import { Close, Menu, Psychology } from '@mui/icons-material';

interface ChatHeaderProps {
  isSidebarOpen: boolean;
  onToggleSidebar: () => void;
  isDebugMode: boolean;
  currentConversationId: number | null;
  isConfigViewActive: boolean;
  onViewMemory: () => void;
  isLoadingMemory: boolean;
}

const ChatHeader: React.FC<ChatHeaderProps> = ({
  isSidebarOpen,
  onToggleSidebar,
  isDebugMode,
  currentConversationId,
  isConfigViewActive,
  onViewMemory,
  isLoadingMemory,
}) => {
  return (
    <div className="lg:hidden mobile-header">
      <button
        onClick={onToggleSidebar}
        className="btn-glass"
        aria-label="Toggle sidebar"
      >
        {isSidebarOpen ? <Close fontSize="medium" /> : <Menu fontSize="medium" />}
      </button>
      
      <div className="flex items-center space-x-2">
        <span className="text-white font-medium text-lg">Curiosity Coach</span>
        <span className="text-2xl">🤔</span>
      </div>
      
      {isDebugMode && currentConversationId && !isConfigViewActive && (
        <button
          onClick={onViewMemory}
          className="btn-gradient-secondary"
          title="See AI Generated Memory for this conversation"
          disabled={isLoadingMemory}
        >
          <Psychology fontSize="small" className="mr-1"/>
          <span className="hidden sm:inline">
            {isLoadingMemory ? 'Loading...' : 'Memory'}
          </span>
        </button>
      )}
    </div>
  );
};

export default ChatHeader;