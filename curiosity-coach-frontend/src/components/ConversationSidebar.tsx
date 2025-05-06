import React from 'react';
import { useChat } from '../context/ChatContext';

const ConversationSidebar: React.FC = () => {
  const {
    conversations,
    currentConversationId,
    selectConversation,
    handleCreateConversation,
    isLoadingConversations,
    setIsConfigViewActive,
    isConfigViewActive
  } = useChat();

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
                <button
                  onClick={() => selectConversation(conv.id)}
                  className={`w-full text-left px-4 py-3 hover:bg-gray-700 focus:outline-none focus:bg-gray-700 transition duration-150 ease-in-out ${ 
                    conv.id === currentConversationId ? 'bg-gray-900 font-semibold' : '' 
                  }`}
                >
                  {conv.title || 'Untitled Chat'}
                  {/* Optional: Display date/time relative to now */}
                  <span className="block text-xs text-gray-400 mt-1">
                    {new Date(conv.updated_at).toLocaleDateString()}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Optional: Footer/User Info */}
      {/* <div className="p-4 border-t border-gray-700">User Info</div> */}

      {/* Brain Config Button */}
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
    </div>
  );
};

export default ConversationSidebar; 