import React from 'react';
import { useChat } from '../context/ChatContext';
import { useLocation } from 'react-router-dom';

const ConversationSidebar: React.FC = () => {
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

  const location = useLocation();
  const isChatEndpoint = location.pathname === '/chat';

  const [editingConversationId, setEditingConversationId] = React.useState<number | null>(null);
  const [editingTitle, setEditingTitle] = React.useState<string>('');
  const inputRef = React.useRef<HTMLInputElement>(null);

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
    // TODO: Call context function to update title
    // await handleUpdateConversationTitle(editingConversationId, editingTitle.trim());
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
  };

  return (
    <div className="w-64 bg-gray-800 text-white flex flex-col h-screen">
      {/* Header / New Chat Button */}
      <div className="p-4 border-b border-gray-700">
        <button 
          onClick={() => handleCreateConversation()} 
          className="w-full bg-indigo-500 hover:bg-indigo-600 text-white font-bold py-2 px-4 rounded transition duration-150 ease-in-out"
        >
          + New Chat
        </button>
      </div>

      {/* Conversation List */}
      <div className="flex-1 overflow-y-auto">
        {isLoadingConversations ? (
          <div className="p-4 text-center text-gray-400">Loading chats...</div>
        ) : conversations.length === 0 ? (
          <div className="p-4 text-center text-gray-400">No chats yet.</div>
        ) : (
          <ul>
            {conversations.map((conv) => (
              <li key={conv.id}>
                {editingConversationId === conv.id ? (
                  <div className="p-2">
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
                      className="w-full p-2 border border-gray-600 rounded bg-gray-700 text-white text-sm focus:ring-indigo-500 focus:border-indigo-500 disabled:opacity-50"
                      disabled={isUpdatingConversationTitle}
                    />
                    <div className="mt-2 flex justify-end space-x-2">
                      <button
                        onClick={handleSaveEdit}
                        className="px-2 py-1 bg-green-500 hover:bg-green-600 text-white text-xs rounded disabled:opacity-50"
                        disabled={isUpdatingConversationTitle || !editingTitle.trim()}
                      >
                        {isUpdatingConversationTitle ? 'Saving...' : 'Save'}
                      </button>
                      <button
                        onClick={handleCancelEdit}
                        className="px-2 py-1 bg-red-500 hover:bg-red-600 text-white text-xs rounded disabled:opacity-50"
                        disabled={isUpdatingConversationTitle}
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : (
                  <button
                    onClick={() => selectConversation(conv.id)}
                    onDoubleClick={() => handleDoubleClick(conv)}
                    className={`w-full text-left px-4 py-3 hover:bg-gray-700 focus:outline-none focus:bg-gray-700 transition duration-150 ease-in-out ${
                      conv.id === currentConversationId && !isConfigViewActive ? 'bg-gray-900 font-semibold' : ''
                    }`}
                    title={conv.title || 'Untitled Chat'}
                  >
                    <div className="truncate">{conv.title || 'Untitled Chat'}</div>
                    {/* Optional: Display date/time relative to now */}
                    <span className="block text-xs text-gray-400 mt-1">
                      {new Date(conv.updated_at).toLocaleDateString()}
                    </span>
                  </button>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Optional: Footer/User Info */}
      {/* <div className="p-4 border-t border-gray-700">User Info</div> */}

      {/* Brain Config Button - Hide for the /chat endpoint */}
      {!isChatEndpoint && (
        <div className="p-4 border-t border-gray-700">
          <button 
            onClick={handleBrainConfigClick}
            className={`w-full bg-teal-500 hover:bg-teal-600 text-white font-bold py-2 px-4 rounded transition duration-150 ease-in-out ${
              isConfigViewActive ? 'bg-teal-700' : ''
            }`}
          >
            Brain Config
          </button>
        </div>
      )}
    </div>
  );
};

export default ConversationSidebar; 