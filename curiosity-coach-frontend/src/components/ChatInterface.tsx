import React, { useState, useEffect, useRef } from 'react';
import { CircularProgress } from '@mui/material';
import ChatMessage from './ChatMessage';
import ConversationSidebar from './ConversationSidebar';
import { useChat } from '../context/ChatContext';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { LogoutOutlined, Send } from '@mui/icons-material';

const ChatInterface: React.FC = () => {
  const {
    messages,
    currentConversationId,
    isLoadingMessages,
    isSendingMessage,
    error: chatError,
    handleSendMessage: handleSendMessageContext,
    selectConversation,
    isBrainProcessing
  } = useChat();

  const [newMessage, setNewMessage] = useState('');
  const { user, logout } = useAuth();

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  useEffect(() => {
    setTimeout(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, 100); 
  }, [messages]);

  const handleFormSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newMessage.trim() || !user || isSendingMessage || currentConversationId === null) return;

    const contentToSend = newMessage.trim();
    setNewMessage('');

    await handleSendMessageContext(contentToSend);
  };

  const handleLogout = () => {
    logout();
    selectConversation(null);
    navigate('/');
  };

  return (
    <div className="flex h-screen bg-gray-100">
      <ConversationSidebar />
      
      <div className="flex-1 flex flex-col h-screen">
        <header className="bg-white shadow-xs border-b border-gray-200">
          <div className="px-6 py-3 flex justify-between items-center">
            <div>
              <h2 className="text-lg font-semibold text-gray-800">
                {currentConversationId ? `Chat` : 'Curiosity Coach'}
              </h2>
              {user && (
                <p className="text-xs text-gray-500">
                  Logged in as: {user.phone_number}
                </p>
              )}
            </div>
            <button 
              onClick={handleLogout}
              className="flex items-center px-3 py-1.5 bg-red-500 text-white rounded hover:bg-red-600 transition duration-150 ease-in-out text-sm"
              title="Logout"
            >
              <LogoutOutlined fontSize="small" className="mr-1"/> 
              Logout
            </button>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50">
          {currentConversationId === null ? (
             <div className="flex justify-center items-center h-full">
                <p className="text-gray-500">Select a conversation or start a new one.</p>
             </div>
          ) : isLoadingMessages ? (
            <div className="flex justify-center items-center h-full">
              <CircularProgress />
            </div>
          ) : messages.length === 0 ? (
            <div className="flex justify-center items-center h-full">
              <p className="text-gray-500">Send a message to start chatting!</p>
            </div>
          ) : (
            messages.map((msg, index) => (
              <ChatMessage key={msg.id || `msg-${index}`} message={msg} /> 
            ))
          )}
          {chatError && (
            <div className="text-center text-red-500 bg-red-100 p-2 rounded">Error: {chatError}</div>
          )}
          {isBrainProcessing && (
            <div className="flex justify-start pl-2">
                <div className="bg-gray-200 text-gray-700 rounded-lg px-4 py-2 max-w-xs lg:max-w-md shadow animate-pulse">
                  Thinking...
                </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </main>

        <footer className="bg-white p-4 border-t border-gray-200">
          <form onSubmit={handleFormSubmit} className="flex items-center space-x-3">
            <textarea
              className="flex-1 resize-none border rounded-md p-2 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
              rows={1}
              placeholder={currentConversationId === null ? "Select a conversation first..." : "Type your message..."}
              value={newMessage}
              onChange={(e) => setNewMessage(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleFormSubmit(e);
                }
              }}
              disabled={isSendingMessage || currentConversationId === null}
            />
            <button
              type="submit"
              className={`px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed ${isSendingMessage ? 'animate-pulse' : ''}`}
              disabled={!newMessage.trim() || isSendingMessage || currentConversationId === null}
            >
              {isSendingMessage ? (
                  <CircularProgress size={20} color="inherit" />
              ) : (
                  <Send fontSize="small" />
              )}
            </button>
          </form>
        </footer>
      </div>
    </div>
  );
};

export default ChatInterface; 