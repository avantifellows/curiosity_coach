import React, { createContext, useState, useContext, useEffect, ReactNode, useCallback } from 'react';
import {
  listConversations,
  createConversation,
  getConversationMessages,
  sendMessage,
  getAiResponseForUserMessage
} from '../services/api';
import { ConversationSummary, Conversation, Message, ChatHistory } from '../types';
import { useAuth } from './AuthContext'; // Assuming AuthContext provides user info

interface ChatContextState {
  conversations: ConversationSummary[];
  currentConversationId: number | null;
  messages: Message[];
  isLoadingConversations: boolean;
  isLoadingMessages: boolean;
  isSendingMessage: boolean;
  isBrainProcessing: boolean;
  error: string | null;
  fetchConversations: () => Promise<void>;
  selectConversation: (conversationId: number | null) => void;
  handleSendMessage: (content: string) => Promise<void>;
  handleCreateConversation: (title?: string) => Promise<void>;
}

const ChatContext = createContext<ChatContextState | undefined>(undefined);

export const ChatProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [currentConversationId, setCurrentConversationId] = useState<number | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoadingConversations, setIsLoadingConversations] = useState(false);
  const [isLoadingMessages, setIsLoadingMessages] = useState(false);
  const [isSendingMessage, setIsSendingMessage] = useState(false);
  const [isBrainProcessing, setIsBrainProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { user } = useAuth(); // Get user from AuthContext to fetch data only when logged in

  // --- Fetch Conversations --- 
  const fetchConversations = useCallback(async () => {
    if (!user) return; // Don't fetch if not logged in
    setIsLoadingConversations(true);
    setError(null);
    try {
      const fetchedConversations = await listConversations();
      setConversations(fetchedConversations);
      // Optionally select the most recent conversation by default
      // if (fetchedConversations.length > 0 && currentConversationId === null) {
      //   setCurrentConversationId(fetchedConversations[0].id);
      // }
    } catch (err: any) {
      setError(err.message || 'Failed to fetch conversations');
    } finally {
      setIsLoadingConversations(false);
    }
  }, [user]); // Depend on user

  // --- Fetch Messages for a Conversation --- 
  const fetchMessages = useCallback(async (conversationId: number) => {
    if (!user) return;
    setIsLoadingMessages(true);
    setIsBrainProcessing(false);
    setError(null);
    setMessages([]); // Clear previous messages
    try {
      const history: ChatHistory = await getConversationMessages(conversationId);
      setMessages(history.messages || []); // Assuming ChatHistory has a messages array
    } catch (err: any) {
      setError(err.message || 'Failed to fetch messages');
      setMessages([]); // Clear messages on error
    } finally {
      setIsLoadingMessages(false);
    }
  }, [user]);

  // --- Select Conversation --- 
  const selectConversation = useCallback((conversationId: number | null) => {
    setCurrentConversationId(conversationId);
    setIsBrainProcessing(false);
    if (conversationId !== null) {
      fetchMessages(conversationId);
    } else {
      setMessages([]); // Clear messages if no conversation is selected
    }
  }, [fetchMessages]);

  // --- Poll for AI Response --- 
  const pollAiResponse = useCallback(async (userMessageId: number, currentConvId: number | null): Promise<(() => void) | undefined> => {
      if (currentConvId === null) {
          setIsBrainProcessing(false);
          return; 
      }

      let pollInterval: NodeJS.Timeout | null = null;
      let isPolling = true;

      const stopPolling = () => {
        if (pollInterval) clearInterval(pollInterval);
        isPolling = false;
        setCurrentConversationId(prevConvId => {
            if (prevConvId === currentConvId) {
                setIsBrainProcessing(false);
            }
            return prevConvId; 
        });
      };

      pollInterval = setInterval(async () => {
          if (!isPolling) return;
          try {
              const aiMessage = await getAiResponseForUserMessage(userMessageId);
              if (aiMessage) {
                  setCurrentConversationId(prevConvId => {
                      // Only update state if the conversation hasn't changed
                      if (prevConvId === currentConvId) {
                          setMessages(prevMessages => {
                              // Check if the message ID already exists
                              const messageExists = prevMessages.some(msg => msg.id === aiMessage.id);
                              // Only add the message if it doesn't already exist
                              if (!messageExists) {
                                  return [...prevMessages, { ...aiMessage, status: 'sent' }];
                              }
                              // If it exists, return the previous state unchanged
                              return prevMessages;
                          });
                      }
                      return prevConvId;
                  });
                  stopPolling();
              }
          } catch (pollError: any) {
              console.error("Polling error:", pollError);
              stopPolling(); // Stop polling on error too
          }
      }, 3000);

      return stopPolling;

  }, []);

  // --- Send Message --- 
  let cleanupPolling: (() => void) | undefined | null = null;

  useEffect(() => {
    return () => {
        if (cleanupPolling) {
            cleanupPolling();
        }
    };
  }, [cleanupPolling]);

  const handleSendMessage = useCallback(async (content: string) => {
    if (currentConversationId === null) {
      setError('No conversation selected');
      return;
    }

    if (cleanupPolling) {
        cleanupPolling();
        cleanupPolling = null;
    }
    
    setIsSendingMessage(true);
    setIsBrainProcessing(false);
    setError(null);
    
    const tempUserMessage: Message = {
        id: Date.now(),
        content,
        is_user: true,
        timestamp: new Date().toISOString(),
        status: 'sending',
    };

    setMessages(prev => [...prev, tempUserMessage]);

    try {
      const response = await sendMessage(currentConversationId, content);
      
      if (!response.success || !response.message || typeof response.message.id !== 'number') {
          console.error("Invalid response from sendMessage:", response);
          throw new Error("Failed to save message or invalid response received.");
      }
      
      const savedUserMessage = response.message; 
      
      setMessages(prev => prev.map(msg => 
          msg.id === tempUserMessage.id 
          ? { ...savedUserMessage, status: 'sent' } 
          : msg
      ));
      
      setIsBrainProcessing(true); 
      
      const stopPollingCallback = await pollAiResponse(savedUserMessage.id!, currentConversationId);
      if (typeof stopPollingCallback === 'function') {
          cleanupPolling = stopPollingCallback;
      }

    } catch (err: any) {
      setError(err.message || 'Failed to send message');
      setMessages(prev => prev.map(msg => 
          msg.id === tempUserMessage.id 
          ? { ...msg, status: 'error' } 
          : msg
      ));
      setIsBrainProcessing(false);
    } finally {
      setIsSendingMessage(false);
    }
  }, [currentConversationId, pollAiResponse]);

  // --- Create Conversation --- 
  const handleCreateConversation = useCallback(async (title?: string) => {
    if (!user) return;
    // Consider adding loading state for creation
    setError(null);
    try {
      const newConversation = await createConversation(title);
      setConversations(prev => [newConversation, ...prev]); // Add to top of list
      setCurrentConversationId(newConversation.id);
      setMessages([]); // Clear messages for new chat
    } catch (err: any) {
      setError(err.message || 'Failed to create conversation');
    }
  }, [user]);

  // --- Initial Fetch --- 
  useEffect(() => {
    if (user) {
      fetchConversations();
    } else {
       setConversations([]);
       setCurrentConversationId(null);
       setMessages([]);
       setError(null);
       setIsBrainProcessing(false);
       if (cleanupPolling) cleanupPolling();
    }
    return () => {
      if (cleanupPolling) {
          cleanupPolling();
      }
    };
  }, [user, fetchConversations]);

  // --- Value Provided by Context ---
  const value: ChatContextState = {
    conversations,
    currentConversationId,
    messages,
    isLoadingConversations,
    isLoadingMessages,
    isSendingMessage,
    isBrainProcessing,
    error,
    fetchConversations,
    selectConversation,
    handleSendMessage,
    handleCreateConversation,
  };

  return <ChatContext.Provider value={value}>{children}</ChatContext.Provider>;
};

// --- Custom Hook to use ChatContext --- 
export const useChat = (): ChatContextState => {
  const context = useContext(ChatContext);
  if (context === undefined) {
    throw new Error('useChat must be used within a ChatProvider');
  }
  return context;
}; 