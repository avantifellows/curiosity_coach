import React, { useState, useEffect, useRef, useCallback } from 'react';
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
  
  // Store the ID of the last message received to avoid duplicates
  const lastMessageTimestamp = useRef<string | null>(null); 

  // Refactored function to fetch chat history
  const fetchChatHistory = useCallback(async () => {
    if (!user) return; // Don't fetch if user is not available

    try {
      // setLoading(true); // Optionally remove or keep loader for polling updates
      const response = await getChatHistory();
      // Ensure we only work with messages that have a timestamp
      const fetchedMessages = (response.messages || []).filter((m): m is Message & { timestamp: string } => typeof m.timestamp === 'string'); 

      // Merge new messages, avoiding duplicates based on ID
      setMessages((prevMessages) => {
        // Use a Set of existing IDs for quick lookup
        const existingIds = new Set(prevMessages.map(m => m.id).filter(id => id !== undefined));
        // Filter out duplicates based on ID and ensure timestamp exists
        const newMessages = fetchedMessages.filter(m => m.id !== undefined && !existingIds.has(m.id)); 
        // Log updated to reflect ID check
        console.log('[HISTORY FETCH] Prev count:', prevMessages.length, 'Fetched count:', fetchedMessages.length, 'New messages (by ID) count:', newMessages.length); 
        if (newMessages.length === 0) return prevMessages; // No new messages to add

        // Sort messages by timestamp just in case
        const allMessages = [...prevMessages, ...newMessages].sort(
          (a, b) => {
            // Add checks for timestamp existence during sort comparison
            const timeA = a.timestamp ? new Date(a.timestamp).getTime() : 0; 
            const timeB = b.timestamp ? new Date(b.timestamp).getTime() : 0;
            return timeA - timeB;
          }
        );
        // Update the ref for the last known timestamp
        if (allMessages.length > 0) {
            // Ensure the last message has a timestamp before assigning
            const lastTimestamp = allMessages[allMessages.length - 1].timestamp;
            if (lastTimestamp) { 
                lastMessageTimestamp.current = lastTimestamp;
            }
        }
        console.log('[HISTORY FETCH] Merged state length:', allMessages.length);
        return allMessages;
      });

    } catch (err: any) {
      setError('Failed to load chat history. Polling may be interrupted.');
      console.error('Fetch history error:', err);
    } finally {
      // setLoading(false); // Optionally remove or keep loader
    }
  }, [user]); // Depends on user

  // Fetch initial chat history when component mounts
  useEffect(() => {
    if (user && !authLoading) {
      setLoading(true); // Show loader only for initial load
      fetchChatHistory().finally(() => setLoading(false));
    }
  }, [user, authLoading, fetchChatHistory]);
  
  // Set up polling for new messages
  useEffect(() => {
    if (!user) return; // Only poll if user is logged in

    const intervalId = setInterval(() => {
      fetchChatHistory();
    }, 5000); // Poll every 5 seconds

    // Clear interval on component unmount
    return () => clearInterval(intervalId); 
  }, [user, fetchChatHistory]); // Re-run if user or fetch function changes

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!newMessage.trim() || !user) return;
    
    const contentToSend = newMessage.trim();
    setNewMessage(''); // Clear input immediately
    setError(null);
    setLoading(true); // Show loading indicator while sending

    try {
      // Send message to backend and get the saved message back
      const response = await sendMessage(contentToSend); 
      
      // Check if the response contains the message object with an ID
      if (response.success && response.message && response.message.id) {
        const savedMessage: Message = response.message;
        
        // Add the message returned from the backend to the state
        setMessages((prev) => {
          // Optional: Double-check if this ID already exists before adding
          // (Might be redundant if fetchHistory is quick, but safe)
          const exists = prev.some(m => m.id === savedMessage.id);
          if (exists) {
             console.warn('[SEND MSG] Message already exists in state:', savedMessage.id);
             return prev;
          }
          console.log('[SEND MSG SUCCESS] Adding message from backend:', savedMessage);
          return [...prev, savedMessage];
        });
      } else {
         // Handle cases where the backend response might not be as expected
         console.error('Send message API response missing message data:', response);
         setError('Failed to confirm message sent. It might appear after a refresh.');
         // Optionally, revert UI or keep the optimistic message (if we had one)
      }
      
    } catch (err: any) {
      setError('Failed to send message. Please try again.');
      // Consider reverting optimistic update if we were using one
      console.error('Send message error:', err);
    } finally {
       setLoading(false); // Stop loading indicator after send attempt
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
      <header className="bg-white shadow-xs">
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
            className="p-2 rounded-full hover:bg-gray-100 focus:outline-hidden focus:ring-2 focus:ring-primary"
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