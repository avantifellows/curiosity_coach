import React, { useState, useEffect, useRef, useCallback } from 'react';
import { CircularProgress } from '@mui/material';
import { useAuth } from '../context/AuthContext';
import { sendMessage, getChatHistory, getAiResponseForUserMessage } from '../services/api';
import { Message } from '../types';
import ChatMessage from './ChatMessage';
import { useNavigate } from 'react-router-dom';
import { LogoutOutlined, Send } from '@mui/icons-material';

// Define a type that includes the optional status and allows string/number ID
interface DisplayMessage extends Omit<Message, 'id' | 'is_user'> { // Omit original id and is_user
  id: number | string; // Allow string for temp ID
  sender: 'user' | 'ai'; // Use sender for display logic
  is_user?: boolean; // Keep original for potential backend use
  status?: 'sending' | 'sent' | 'failed';
  timestamp: string; // Ensure timestamp is always present for sorting/display
}

const ChatInterface: React.FC = () => {
  const [messages, setMessages] = useState<DisplayMessage[]>([]); // Use updated DisplayMessage
  const [newMessage, setNewMessage] = useState('');
  const [loadingInitial, setLoadingInitial] = useState(false); // Renamed for clarity
  const [sendingMessage, setSendingMessage] = useState(false); // Track sending state separately
  const [isAiThinking, setIsAiThinking] = useState(false); // State to track AI response loading
  const [error, setError] = useState<string | null>(null);
  const { user, isLoading: authLoading, logout } = useAuth();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();
  // Use a ref to store active polling intervals to clear them later
  const pollingIntervals = useRef<Record<string, NodeJS.Timeout>>({});

  // Fetch initial chat history (only runs once on mount)
  const fetchInitialChatHistory = useCallback(async () => {
    if (!user) return;
    setLoadingInitial(true);
    setError(null);
    try {
      const response = await getChatHistory();
      const fetchedMessages = (response.messages || []).filter((m): m is Message & { timestamp: string; id: number } => 
        typeof m.timestamp === 'string' && typeof m.id === 'number' && typeof m.is_user === 'boolean'
      ); // Ensure required fields exist
      // Map backend Message to DisplayMessage
      const initialMessages: DisplayMessage[] = fetchedMessages.map(m => ({
        ...m, 
        sender: m.is_user ? 'user' : 'ai',
        status: 'sent',
        id: m.id, // Explicitly use number ID from backend
        timestamp: m.timestamp // It's guaranteed by the filter
      })); 
      // Sorting uses timestamp which is now guaranteed
      setMessages(initialMessages.sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()));
    } catch (err: any) { // Changed err type to any
      setError('Failed to load initial chat history.');
      console.error('Fetch initial history error:', err);
    } finally {
      setLoadingInitial(false);
    }
  }, [user]);

  // Fetch initial chat history when component mounts and user is loaded
  useEffect(() => {
    if (user && !authLoading) {
      fetchInitialChatHistory();
    }
  }, [user, authLoading, fetchInitialChatHistory]);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Cleanup polling intervals on unmount
  useEffect(() => {
    return () => {
      Object.values(pollingIntervals.current).forEach(clearInterval);
    };
  }, []);

  // Function to poll for AI response for a specific user message ID
  const pollForResponse = useCallback((userMessageId: string | number) => {
    const userMessageIdStr = String(userMessageId);

    if (pollingIntervals.current[userMessageIdStr]) {
      clearInterval(pollingIntervals.current[userMessageIdStr]);
    }

    const intervalId = setInterval(async () => {
      console.log(`[POLLING] Checking for AI response to user message ${userMessageIdStr}`);
      try {
        // Call the new API function to get the specific response
        const response = await getAiResponseForUserMessage(userMessageIdStr);

        // Check if the response contains the AI message
        if (response && response.message && response.message.id && response.message.timestamp && typeof response.message.is_user === 'boolean') { 
          const aiMessageBackend = response.message;
          
          // Map backend Message to DisplayMessage
          const aiMessage: DisplayMessage = {
              content: aiMessageBackend.content,
              user_id: aiMessageBackend.user_id,
              is_user: false,
              id: aiMessageBackend.id!, 
              sender: 'ai',
              status: 'sent',
              timestamp: aiMessageBackend.timestamp!
          };
          
          console.log(`[POLLING] AI Response received for ${userMessageIdStr}:`, aiMessage);

          setMessages((prev) => {
            // Prevent adding duplicates if polling runs quickly or endpoint is called again
            if (prev.some(m => String(m.id) === String(aiMessage.id))) {
              return prev;
            }
            // Add the new message and re-sort
            return [...prev, aiMessage].sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
          });

          // Stop polling for this message ID since we found the response
          clearInterval(intervalId);
          delete pollingIntervals.current[userMessageIdStr];
          setIsAiThinking(false); // <-- Set thinking to false
          console.log(`[POLLING] Stopped polling for ${userMessageIdStr}`);
        } else {
          // If response is null or doesn't contain a message, it means it's not ready yet.
          // Keep polling.
          console.log(`[POLLING] AI Response for ${userMessageIdStr} not ready yet.`);
        }
      } catch (error: any) { // Catch should technically not be needed due to api.ts change, but kept for safety
        // Log unexpected errors during the polling check itself (not API errors handled in api.ts)
        console.error(`[POLLING] Unexpected error polling for response to ${userMessageIdStr}:`, error);
        // Consider stopping polling on repeated unexpected errors? Maybe set isAiThinking(false) here too?
        // For now, let it continue polling as per previous logic.
      }
    }, 3000); // Poll every 3 seconds (adjust as needed)

    pollingIntervals.current[userMessageIdStr] = intervalId;
  }, []); // Keep dependency array empty unless specific state/props needed *directly* in here

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newMessage.trim() || !user || sendingMessage) return;

    const contentToSend = newMessage.trim();
    const tempId = `temp-${Date.now()}`;
    const optimisticMessage: DisplayMessage = {
      // id is string here
      id: tempId, 
      content: contentToSend,
      sender: 'user', // Set sender for display
      is_user: true, // Set is_user for consistency
      timestamp: new Date().toISOString(), // Use current time, guaranteed string
      status: 'sending',
      user_id: user.id // This should be number, matching Message type
    };

    setNewMessage('');
    setError(null);
    setMessages((prev) => [...prev, optimisticMessage]); // Add optimistic message immediately
    setSendingMessage(true); // Indicate sending is in progress

    try {
      const response = await sendMessage(contentToSend);

      if (response.success && response.message && response.message.id && response.message.timestamp && typeof response.message.is_user === 'boolean') {
        // Map backend Message to DisplayMessage before updating state
        const confirmedBackendMessage = response.message;
        // Add non-null assertions (!) since we checked for null/undefined before
        const confirmedMessage: DisplayMessage = { 
            content: confirmedBackendMessage.content, 
            user_id: confirmedBackendMessage.user_id,
            is_user: true, // We know it's the user's confirmed message
            id: confirmedBackendMessage.id!, // Use non-null assertion
            sender: 'user', 
            status: 'sent', 
            timestamp: confirmedBackendMessage.timestamp! // Use non-null assertion
        }; 
        console.log('[SEND MSG SUCCESS] Received confirmation:', confirmedMessage);

        // Update the optimistic message (identified by temp string ID) with the confirmed data (number ID)
        setMessages((prev) =>
          prev.map((msg) =>
            String(msg.id) === tempId ? confirmedMessage : msg // Replace entirely
          )
        );

        // Start polling with the confirmed message ID (number)
        setIsAiThinking(true); // <-- Set thinking to true
        pollForResponse(confirmedMessage.id);

      } else {
        // Handle failure - update the temp message status (identified by temp string ID)
        console.error('Send message API response invalid:', response);
        setError('Failed to send message. Server error.');
        setMessages((prev) =>
          prev.map((msg) =>
            // Compare potentially string/number ID with temp string ID
            String(msg.id) === tempId ? { ...msg, status: 'failed' } : msg
          )
        );
      }
    } catch (err: any) { // Changed err type to any
      console.error('Send message error:', err);
      setError('Failed to send message. Network error.');
      // Update the temp message status to failed (identified by temp string ID)
      setMessages((prev) =>
        prev.map((msg) =>
          // Compare potentially string/number ID with temp string ID
          String(msg.id) === tempId ? { ...msg, status: 'failed' } : msg
        )
      );
    } finally {
      setSendingMessage(false); // Sending attempt finished
    }
  };

  const handleLogout = () => {
    // Clear any active polling before logging out
    Object.values(pollingIntervals.current).forEach(clearInterval);
    pollingIntervals.current = {};
    logout();
    navigate('/');
  };

  if (authLoading) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <div className="flex flex-col items-center">
          <CircularProgress />
          <p className="mt-4 text-gray-600">Authenticating...</p>
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
          {loadingInitial && messages.length === 0 ? (
            <div className="flex justify-center items-center h-full">
              <CircularProgress />
              <p className="ml-3 text-gray-600">Loading chat history...</p>
            </div>
          ) : messages.length === 0 && !loadingInitial && !isAiThinking ? (
            <div className="flex justify-center items-center h-full">
              <p className="text-gray-500">No messages yet. Start a conversation!</p>
            </div>
          ) : (
            <div className="space-y-2">
              {/* Use DisplayMessage type here */}
              {messages.map((message) => (
                // Pass DisplayMessage to ChatMessage component - requires ChatMessage update
                <ChatMessage key={String(message.id)} message={message} /> 
              ))}
              {/* AI Thinking Indicator */}
              {isAiThinking && (
                <div className="flex justify-start items-center space-x-2 ml-2 my-2"> 
                  <CircularProgress size={20} color="inherit" className="text-gray-500" />
                  <p className="text-sm text-gray-500 italic">Thinking...</p>
                </div>
              )}
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
              // Disable input while authenticating, initially loading, or sending a message
              disabled={!user || authLoading || loadingInitial || sendingMessage}
              className="flex-1 mr-3 focus:ring-primary focus:border-primary rounded-full py-2 px-4"
            />
            <button
              type="submit"
              // Disable button based on same conditions + if message is empty
              disabled={!user || authLoading || loadingInitial || sendingMessage || !newMessage.trim()}
              className={`btn-primary rounded-full p-3 flex items-center justify-center transition-opacity duration-200 ${
                !user || authLoading || loadingInitial || sendingMessage || !newMessage.trim() ? 'opacity-50 cursor-not-allowed' : 'hover:bg-primary-dark'
              }`}
              aria-label="Send message"
            >
              {/* Show spinner only when actively sending */}
              {sendingMessage ? <CircularProgress size={24} color="inherit" /> : <Send />}
            </button>
          </form>
        </div>
      </main>
    </div>
  );
};

export default ChatInterface; 