import React, { useState, useEffect, useRef } from 'react';
import { CircularProgress } from '@mui/material';
import { useAuth } from '../context/AuthContext';
import { sendMessage, getChatHistory } from '../services/api';
import { Message } from '../types';
import ChatMessage from './ChatMessage';
import { useNavigate } from 'react-router-dom';
import { LogoutOutlined, Send } from '@mui/icons-material';

const ChatInterface: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [newMessage, setNewMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { user, isLoading: authLoading, logout } = useAuth();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  // Fetch chat history when component mounts
  useEffect(() => {
    const fetchChatHistory = async () => {
      if (!user) return; // Don't fetch if user is not available
      
      try {
        setLoading(true);
        const response = await getChatHistory();
        setMessages(response.messages || []);
      } catch (err: any) {
        setError('Failed to load chat history. Please try again later.');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    if (user && !authLoading) {
      fetchChatHistory();
    }
  }, [user, authLoading]);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!newMessage.trim() || !user) return;
    
    // Optimistically add message to UI
    const userMessage: Message = {
      content: newMessage.trim(),
      is_user: true,
      timestamp: new Date().toISOString(),
    };
    
    setMessages((prev) => [...prev, userMessage]);
    setNewMessage('');
    setError(null);
    
    try {
      // Send message to backend
      await sendMessage(userMessage.content);
      
      // In a real app, you would wait for the response message from the backend
      // For now, we'll simulate a response after a short delay
      setLoading(true);
      
      // This is placeholder - in reality, you would listen for the response from your message queue
      setTimeout(async () => {
        try {
          // Refetch chat history to get the response
          const history = await getChatHistory();
          setMessages(history.messages || []);
        } catch (err) {
          setError('Failed to receive response. Please try again.');
          console.error(err);
        } finally {
          setLoading(false);
        }
      }, 1000);
      
    } catch (err: any) {
      setError('Failed to send message. Please try again.');
      console.error(err);
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  if (authLoading) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <div className="flex flex-col items-center">
          <CircularProgress />
          <p className="mt-4 text-gray-600">Loading chat...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3 flex justify-between items-center">
          <div>
            <h1 className="text-xl font-bold text-gray-900">Curiosity Coach</h1>
            {user && (
              <p className="text-sm text-gray-500">
                Logged in as: {user.phone_number}
              </p>
            )}
          </div>
          <button 
            onClick={handleLogout}
            className="p-2 rounded-full hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-primary"
            aria-label="Logout"
          >
            <LogoutOutlined className="text-gray-600" />
          </button>
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1 overflow-hidden p-4 sm:p-6 md:p-8 flex flex-col max-w-7xl mx-auto w-full">
        {/* Chat messages */}
        <div className="flex-1 overflow-y-auto mb-4 card min-h-0 p-4">
          {loading && messages.length === 0 ? (
            <div className="flex justify-center items-center h-full">
              <CircularProgress />
            </div>
          ) : messages.length === 0 ? (
            <div className="flex justify-center items-center h-full">
              <p className="text-gray-500">No messages yet. Start a conversation!</p>
            </div>
          ) : (
            <div className="space-y-2">
              {messages.map((message, index) => (
                <ChatMessage key={index} message={message} />
              ))}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Message input */}
        <div className="card mt-auto p-4">
          {error && (
            <div className="bg-red-50 border-l-4 border-red-500 p-4 mb-4 text-red-700">
              <p>{error}</p>
            </div>
          )}
          
          <form onSubmit={handleSendMessage} className="flex items-center">
            <input
              type="text"
              placeholder="Type your message..."
              value={newMessage}
              onChange={(e) => setNewMessage(e.target.value)}
              disabled={!user || loading}
              className="flex-1 mr-3 focus:ring-primary focus:border-primary rounded-full py-2 px-4"
            />
            <button
              type="submit"
              disabled={!user || loading || !newMessage.trim()}
              className={`btn-primary rounded-full p-3 flex items-center justify-center ${
                !user || loading || !newMessage.trim() ? 'opacity-50 cursor-not-allowed' : ''
              }`}
            >
              {loading ? <CircularProgress size={24} /> : <Send />}
            </button>
          </form>
        </div>
      </main>
    </div>
  );
};

export default ChatInterface; 