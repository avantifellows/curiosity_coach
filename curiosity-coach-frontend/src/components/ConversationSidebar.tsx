import React from 'react';
import { useChat } from '../context/ChatContext';
import { useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Settings, Add } from '@mui/icons-material';

interface ConversationSidebarProps {
  onConversationSelect?: () => void;
  onOpenFeedbackModal: () => void;
}

const ConversationSidebar: React.FC<ConversationSidebarProps> = ({ onConversationSelect, onOpenFeedbackModal }) => {
  const {
    conversations,
    currentConversationId,
    selectConversation,
    handleCreateConversation,
    isLoadingConversations,
    setIsConfigViewActive,
    isConfigViewActive,
    handleUpdateConversationTitle,
    isUpdatingConversationTitle,
  } = useChat();

  const { user, logout } = useAuth();
  const location = useLocation();
  const isChatEndpoint = location.pathname === '/chat';

  const [editingConversationId, setEditingConversationId] = React.useState<number | null>(null);
  const [editingTitle, setEditingTitle] = React.useState<string>('');
  const inputRef = React.useRef<HTMLInputElement>(null);

  const handleLogout = () => {
    logout();
    selectConversation(null);
  };

  const handleDoubleClick = (conv: { id: number; title: string | null }) => {
    setEditingConversationId(conv.id);
    setEditingTitle(conv.title || 'Untitled Chat');
  };

  const handleTitleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setEditingTitle(e.target.value);
  };

  const handleSaveEdit = async () => {
    if (editingConversationId === null || !editingTitle.trim()) {
      handleCancelEdit();
      return;
    }
    await handleUpdateConversationTitle(editingConversationId, editingTitle.trim());
    setEditingConversationId(null);
    setEditingTitle('');
  };

  const handleCancelEdit = () => {
    setEditingConversationId(null);
    setEditingTitle('');
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Enter') {
      handleSaveEdit();
    } else if (event.key === 'Escape') {
      handleCancelEdit();
    }
  };

  React.useEffect(() => {
    if (editingConversationId !== null && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [editingConversationId]);

  const handleBrainConfigClick = () => {
    selectConversation(null);
    setIsConfigViewActive(true);
    onConversationSelect?.();
  };

  const handleConversationClick = (convId: number) => {
    selectConversation(convId);
    onConversationSelect?.();
  };

  const handleNewChatClick = () => {
    handleCreateConversation();
    onConversationSelect?.();
  };

  // Helper function to get a random emoji for each conversation based on its ID
  const getConversationEmoji = (id: number) => {
    const emojis = ['🚀', '🔍', '💡', '🌈', '🦄', '🌟', '🧠', '🔭', '📚', '🧩', '🔮', '🌍'];
    return emojis[id % emojis.length];
  };

  return (
    <div className="sidebar-main">
      {/* Header / New Chat Button */}
      <div className="sidebar-header">
        <button 
          onClick={handleNewChatClick} 
          className="new-chat-btn"
        >
          <Add className="mr-2" /> New Adventure
        </button>
      </div>

      {/* Conversation List */}
      <div className="conversation-list">
        <h2 className="conversation-list-header">Your Chats</h2>
        
        {isLoadingConversations ? (
          <div className="conversation-list-loading">Loading chats...</div>
        ) : conversations.length === 0 ? (
          <div className="conversation-list-empty">
            <div className="text-3xl mb-2">🔍</div>
            No chats yet.<br/>Start a new adventure!
          </div>
        ) : (
          <ul className="space-y-2">
            {conversations.map((conv) => (
              <li key={conv.id} className="conversation-item">
                {editingConversationId === conv.id ? (
                  <div className="conversation-edit-container">
                    <input
                      ref={inputRef}
                      type="text"
                      value={editingTitle}
                      onChange={handleTitleChange}
                      onKeyDown={handleKeyDown}
                      onBlur={() => setTimeout(() => {
                        if (!isUpdatingConversationTitle && editingConversationId !== null) {
                        }
                      }, 100)}
                      className="conversation-edit-input"
                      disabled={isUpdatingConversationTitle}
                    />
                    <div className="mt-2 flex justify-end space-x-2">
                      <button
                        onClick={handleSaveEdit}
                        className="conversation-edit-btn-save"
                        disabled={isUpdatingConversationTitle || !editingTitle.trim()}
                      >
                        {isUpdatingConversationTitle ? 'Saving...' : 'Save'}
                      </button>
                      <button
                        onClick={handleCancelEdit}
                        className="conversation-edit-btn-cancel"
                        disabled={isUpdatingConversationTitle}
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : (
                  <button
                    onClick={() => handleConversationClick(conv.id)}
                    onDoubleClick={() => handleDoubleClick(conv)}
                    className={conv.id === currentConversationId && !isConfigViewActive 
                        ? 'conversation-btn-active' 
                        : 'conversation-btn-inactive'}
                    title={conv.title || 'Untitled Chat'}
                  >
                    <div className="conversation-emoji">
                      <span>{getConversationEmoji(conv.id)}</span>
                    </div>
                    <div className="conversation-content">
                      <div className="conversation-title">
                        {conv.title || 'Untitled Chat'}
                      </div>
                      <span className="conversation-date">
                        {new Date(conv.updated_at).toLocaleDateString()}
                      </span>
                    </div>
                  </button>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Brain Config Button - Hide for the /chat endpoint */}
      {!isChatEndpoint && (
        <div className="sidebar-section">
          <button 
            onClick={handleBrainConfigClick}
            className={isConfigViewActive ? 'brain-config-btn-active' : 'brain-config-btn'}
          >
            <Settings className="mr-2" /> Brain Config
          </button>
        </div>
      )}

      {/* User Info and Logout Button */}
      {user && (
        <div className="user-info-section">
          <div className="flex flex-col space-y-3">
            <button 
                onClick={onOpenFeedbackModal}
                className="new-chat-btn"
            >
                Give Feedback
            </button>
            <div className="text-center">
                <span className="user-info-text text-sm">
                Logged in as: <span className="font-medium text-white">{user.name || user.phone_number}</span>
                </span>
                <span className="mx-2 text-gray-400">|</span>
                <button 
                onClick={handleLogout}
                className="text-sm text-gray-300 hover:text-white hover:underline transition-colors duration-200"
                >
                Logout
                </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ConversationSidebar; 