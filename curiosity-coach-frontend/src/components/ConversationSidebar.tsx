import React from 'react';
import { useChat } from '../context/ChatContext';
import { useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { LogoutOutlined, Settings, Add } from '@mui/icons-material';

interface ConversationSidebarProps {
  onConversationSelect?: () => void;
}

const ConversationSidebar: React.FC<ConversationSidebarProps> = ({ onConversationSelect }) => {
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
    <div className="w-72 bg-gradient-to-b from-indigo-600 via-indigo-700 to-purple-800 text-white flex flex-col h-screen">
      {/* Header / New Chat Button */}
      <div className="p-5 border-b border-indigo-500/30">
        <button 
          onClick={handleNewChatClick} 
          className="w-full bg-white text-indigo-700 hover:bg-indigo-100 font-bold py-3 px-4 rounded-xl transition-all duration-200 ease-in-out transform hover:scale-105 hover:shadow-lg flex items-center justify-center"
        >
          <Add className="mr-2" /> New Adventure
        </button>
      </div>

      {/* Conversation List */}
      <div className="flex-1 overflow-y-auto px-3 py-4">
        <h2 className="text-indigo-200 text-sm font-semibold uppercase tracking-wider mb-3 px-2">Your Chats</h2>
        
        {isLoadingConversations ? (
          <div className="p-4 text-center text-indigo-200 animate-pulse">Loading chats...</div>
        ) : conversations.length === 0 ? (
          <div className="p-6 text-center text-indigo-200 bg-indigo-800/30 rounded-xl">
            <div className="text-3xl mb-2">🔍</div>
            No chats yet.<br/>Start a new adventure!
          </div>
        ) : (
          <ul className="space-y-2">
            {conversations.map((conv) => (
              <li key={conv.id} className="transition-all duration-200 hover:translate-x-1">
                {editingConversationId === conv.id ? (
                  <div className="p-2 bg-indigo-500/50 rounded-xl">
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
                      className="w-full p-2 border border-indigo-400 rounded-lg bg-indigo-700 text-white text-sm focus:ring-indigo-300 focus:border-indigo-300 disabled:opacity-50"
                      disabled={isUpdatingConversationTitle}
                    />
                    <div className="mt-2 flex justify-end space-x-2">
                      <button
                        onClick={handleSaveEdit}
                        className="px-3 py-1 bg-green-500 hover:bg-green-600 text-white text-xs rounded-lg disabled:opacity-50 transition-colors duration-200"
                        disabled={isUpdatingConversationTitle || !editingTitle.trim()}
                      >
                        {isUpdatingConversationTitle ? 'Saving...' : 'Save'}
                      </button>
                      <button
                        onClick={handleCancelEdit}
                        className="px-3 py-1 bg-red-500 hover:bg-red-600 text-white text-xs rounded-lg disabled:opacity-50 transition-colors duration-200"
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
                    className={`w-full text-left px-4 py-3 rounded-xl transition-all duration-200 ease-in-out flex items-center ${
                      conv.id === currentConversationId && !isConfigViewActive 
                        ? 'bg-indigo-500 shadow-lg' 
                        : 'hover:bg-indigo-500/50'
                    }`}
                    title={conv.title || 'Untitled Chat'}
                  >
                    <div className="w-8 h-8 flex-shrink-0 flex items-center justify-center bg-indigo-400/30 rounded-full mr-3">
                      <span>{getConversationEmoji(conv.id)}</span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="font-medium truncate">
                        {conv.title || 'Untitled Chat'}
                      </div>
                      <span className="block text-xs text-indigo-200 mt-1">
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
        <div className="p-4 border-t border-indigo-500/30">
          <button 
            onClick={handleBrainConfigClick}
            className={`w-full bg-teal-500 hover:bg-teal-600 text-white font-bold py-3 px-4 rounded-xl transition-all duration-200 ease-in-out flex items-center justify-center ${
              isConfigViewActive ? 'bg-teal-700 shadow-inner' : ''
            }`}
          >
            <Settings className="mr-2" /> Brain Config
          </button>
        </div>
      )}

      {/* User Info and Logout Button */}
      {user && (
        <div className="p-4 border-t border-indigo-500/30 bg-indigo-900/30">
          <div className="flex flex-col space-y-3">
            <div className="text-sm text-indigo-200">
              Logged in as: <span className="font-medium text-white">{user.phone_number}</span>
            </div>
            <button 
              onClick={handleLogout}
              className="w-full flex items-center justify-center bg-red-500 hover:bg-red-600 text-white py-2 px-4 rounded-xl transition-all duration-200 ease-in-out hover:shadow-lg"
            >
              <LogoutOutlined fontSize="small" className="mr-2" />
              Logout
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default ConversationSidebar; 