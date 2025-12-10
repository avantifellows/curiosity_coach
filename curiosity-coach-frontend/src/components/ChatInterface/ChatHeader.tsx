import React from 'react';
import { Close, Menu, Psychology, Logout } from '@mui/icons-material';
import { User } from '../../types';

interface ChatHeaderProps {
  isSidebarOpen: boolean;
  onToggleSidebar?: () => void;
  isDebugMode: boolean;
  currentConversationId: number | null;
  isConfigViewActive: boolean;
  onViewMemory: () => void;
  isLoadingMemory: boolean;
  currentVisitNumber: number | null;
  user: User | null;
  onLogout: () => void;
}

const ChatHeader: React.FC<ChatHeaderProps> = ({
  isSidebarOpen,
  onToggleSidebar,
  isDebugMode,
  currentConversationId,
  isConfigViewActive,
  onViewMemory,
  isLoadingMemory,
  currentVisitNumber,
  user,
  onLogout,
}) => {
  // Show logout button for visits 1-3 (when sidebar is hidden)
  const shouldShowLogout = currentVisitNumber !== null && currentVisitNumber >= 1 && currentVisitNumber <= 3;

  // Show header on desktop when sidebar is hidden (visits 1-3), always show on mobile
  const headerClasses = shouldShowLogout
    ? "mobile-header" // Show on all screen sizes for visits 1-3
    : "lg:hidden mobile-header"; // Hide on desktop for visits 4+ (sidebar visible)

  return (
    <div className={headerClasses}>
      <div className="flex items-center space-x-2">
        {onToggleSidebar && (
          <button
            onClick={onToggleSidebar}
            className="btn-glass"
            aria-label="Toggle sidebar"
          >
            {isSidebarOpen ? <Close fontSize="medium" /> : <Menu fontSize="medium" />}
          </button>
        )}
        {!onToggleSidebar && <div className="w-10"></div>}

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

      <div className="flex items-center space-x-2">
        <span className="text-white font-medium text-lg">Curiosity Coach</span>
        <span className="text-2xl">🤔</span>
      </div>

      <div className="flex items-center space-x-2">
        {shouldShowLogout && user && (
          <button
            onClick={onLogout}
            className="text-sm text-gray-300 hover:text-white hover:underline transition-colors duration-200 flex items-center"
            title="Logout"
          >
            <Logout fontSize="small" className="mr-1" />
            <span className="hidden sm:inline">Logout</span>
          </button>
        )}
      </div>
    </div>
  );
};

export default ChatHeader;