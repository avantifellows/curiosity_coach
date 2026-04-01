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

  // If there is no sidebar toggle, the header is the only persistent navigation surface.
  const headerClasses = !onToggleSidebar || shouldShowLogout
    ? 'mobile-header'
    : 'lg:hidden mobile-header';

  return (
    <div className={headerClasses}>
      <div className="flex min-w-[44px] items-center space-x-2">
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

      <div className="flex min-w-0 items-center justify-center space-x-2 px-2">
        <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-violet-100 text-sm text-violet-700">
          ✦
        </span>
        <span className="truncate text-base font-semibold text-slate-900 sm:text-lg">
          Curiosity Coach
        </span>
      </div>

      <div className="flex min-w-[44px] items-center justify-end space-x-2">
        {shouldShowLogout && user && (
          <button
            onClick={onLogout}
            className="flex items-center text-sm text-slate-500 transition-colors duration-200 hover:text-slate-900"
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
