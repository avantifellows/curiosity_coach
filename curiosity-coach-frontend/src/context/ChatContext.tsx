import React, { createContext, useState, useContext, useEffect, ReactNode, useCallback, useRef } from 'react';
import {
  listConversations,
  createConversation,
  getConversationMessages,
  sendMessage,
  getAiResponseForUserMessage,
  updateConversationTitleApi
} from '../services/api';
import { ConversationSummary, Message, ChatHistory } from '../types';
import { useAuth } from './AuthContext'; // Assuming AuthContext provides user info

// Helper function to extract first 10 words from text
const extractFirstTenWords = (text: string): string => {
  const words = text.trim().split(/\s+/);
  const firstTenWords = words.slice(0, 10).join(' ');
  return firstTenWords || 'New Chat'; // Fallback if no words
};

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
  handleSendMessage: (content: string, purpose: string) => Promise<void>;
  handleSendMessageWithAutoConversation: (content: string, purpose: string) => Promise<void>;
  handleCreateConversation: (title?: string) => Promise<number | null>;

  // New state for Brain Config View
  isConfigViewActive: boolean;
  setIsConfigViewActive: (isActive: boolean) => void;
  brainConfigSchema: any | null; // To store the fetched JSON schema
  isLoadingBrainConfig: boolean;
  brainConfigError: string | null;
  fetchBrainConfigSchema: () => Promise<void>;

  // New state and function for updating Brain Config
  isSavingBrainConfig: boolean;
  saveBrainConfigError: string | null;
  updateBrainConfig: (newConfig: any) => Promise<boolean>; // Returns true on success

  // New state and function for updating Conversation Title
  isUpdatingConversationTitle: boolean;
  updateConversationTitleError: string | null;
  handleUpdateConversationTitle: (conversationId: number, newTitle: string) => Promise<void>;
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

  // New state for Brain Config
  const [isConfigViewActive, setIsConfigViewActive] = useState(false);
  const [brainConfigSchema, setBrainConfigSchema] = useState<any | null>(null);
  const [isLoadingBrainConfig, setIsLoadingBrainConfig] = useState(false);
  const [brainConfigError, setBrainConfigError] = useState<string | null>(null);

  // New state for saving brain config
  const [isSavingBrainConfig, setIsSavingBrainConfig] = useState(false);
  const [saveBrainConfigError, setSaveBrainConfigError] = useState<string | null>(null);

  // New state for updating conversation title
  const [isUpdatingConversationTitle, setIsUpdatingConversationTitle] = useState(false);
  const [updateConversationTitleError, setUpdateConversationTitleError] = useState<string | null>(null);

  const { user } = useAuth(); // Get user from AuthContext to fetch data only when logged in
  const cleanupPollingRef = useRef<(() => void) | null>(null); // Ref to hold the cleanup function

  // --- Function to update title based on first message ---
  const updateTitleFromFirstMessage = useCallback((conversationId: number, content: string, currentMessagesLength: number) => {
    if (currentMessagesLength === 0) { // This is the first message in the conversation
      const newTitle = extractFirstTenWords(content);
      return newTitle;
    }
    return null;
  }, []);

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
      setIsConfigViewActive(false); // Ensure config view is not active when a chat is selected
    } else {
      setMessages([]); // Clear messages if no conversation is selected
    }
  }, [fetchMessages]);

  // --- Update Conversation Title ---
  const handleUpdateConversationTitle = useCallback(async (conversationId: number, newTitle: string) => {
    if (!user) {
      setUpdateConversationTitleError("User not authenticated.");
      return;
    }
    if (!newTitle.trim()) {
      setUpdateConversationTitleError("Title cannot be empty.");
      // Or, revert to original, or let UI handle this (e.g. disable save if empty)
      return;
    }

    setIsUpdatingConversationTitle(true);
    setUpdateConversationTitleError(null);

    try {
      const updatedConversation = await updateConversationTitleApi(conversationId, newTitle.trim());

      setConversations(prevConvs =>
        prevConvs.map(conv =>
          conv.id === conversationId ? { 
            ...conv, // Spread existing summary fields
            title: updatedConversation.title, 
            updated_at: updatedConversation.updated_at 
          } : conv
        )
      );

    } catch (err: any) {
      console.error("Failed to update conversation title:", err);
      setUpdateConversationTitleError(err.message || 'An unknown error occurred while updating title');
    } finally {
      setIsUpdatingConversationTitle(false);
    }
  }, [user]);

  // --- Create Conversation --- 
  const handleCreateConversation = useCallback(async (title?: string): Promise<number | null> => {
    if (!user) return null;
    // Consider adding loading state for creation
    setError(null);
    try {
      const newConversation = await createConversation(title);
      setConversations(prev => [newConversation, ...prev]); // Add to top of list
      setCurrentConversationId(newConversation.id);
      setMessages([]); // Clear messages for new chat
      setIsConfigViewActive(false); // Ensure config view is not active
      return newConversation.id;
    } catch (err: any) {
      setError(err.message || 'Failed to create conversation');
      return null;
    }
  }, [user]);

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
              // Ensure brain processing is turned off even if polling fails,
              // but only if the conversation hasn't changed
              setCurrentConversationId(prevConvId => {
                  if (prevConvId === currentConvId) {
                     setIsBrainProcessing(false);
                  }
                  return prevConvId;
              });
              stopPolling(); // Stop polling on error too
          }
      }, 3000);

      return stopPolling;

  }, []);

  // --- Send Message --- 
  const handleSendMessage = useCallback(async (content: string, purpose: string = "chat") => {
    if (currentConversationId === null) {
      setError('No conversation selected');
      return;
    }

    // Clear any previous polling before starting a new send
    if (cleanupPollingRef.current) {
        cleanupPollingRef.current();
        cleanupPollingRef.current = null;
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

    // Store current message length before adding new message
    const currentMessagesLength = messages.length;

    setMessages(prev => [...prev, tempUserMessage]);

    try {
      const response = await sendMessage(currentConversationId, content, purpose);
      
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
      
      // Check if title should be updated
      const newTitle = updateTitleFromFirstMessage(currentConversationId, content, currentMessagesLength);
      if (newTitle) {
        // Update the title using the existing function
        handleUpdateConversationTitle(currentConversationId, newTitle).catch(err => {
          console.error("Failed to update conversation title:", err);
        });
      }
      
      setIsBrainProcessing(true); 
      
      const stopPollingCallback = await pollAiResponse(savedUserMessage.id!, currentConversationId);
      if (typeof stopPollingCallback === 'function') {
          cleanupPollingRef.current = stopPollingCallback; // Store cleanup in ref
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
  }, [currentConversationId, pollAiResponse, messages, updateTitleFromFirstMessage, handleUpdateConversationTitle]);

  // --- Send Message with Auto-Conversation Creation --- 
  const handleSendMessageWithAutoConversation = useCallback(async (content: string, purpose: string = "chat") => {
    if (!user) {
      setError('User not authenticated');
      return;
    }

    let conversationId = currentConversationId;

    // If no conversation is selected, create one first
    if (conversationId === null) {
      try {
        conversationId = await handleCreateConversation();
        if (conversationId === null) {
          setError('Failed to create conversation');
          return;
        }
      } catch (err: any) {
        setError(err.message || 'Failed to create conversation');
        return;
      }
    }

    // Store current message length before adding new message
    const currentMessagesLength = messages.length;

    // Now send the message with the conversation ID
    // Clear any previous polling before starting a new send
    if (cleanupPollingRef.current) {
        cleanupPollingRef.current();
        cleanupPollingRef.current = null;
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
      const response = await sendMessage(conversationId, content, purpose);
      
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
      
      // Check if title should be updated
      const newTitle = updateTitleFromFirstMessage(conversationId, content, currentMessagesLength);
      if (newTitle) {
        // Update the title using the existing function
        handleUpdateConversationTitle(conversationId, newTitle).catch(err => {
          console.error("Failed to update conversation title:", err);
        });
      }
      
      setIsBrainProcessing(true); 
      
      const stopPollingCallback = await pollAiResponse(savedUserMessage.id!, conversationId);
      if (typeof stopPollingCallback === 'function') {
          cleanupPollingRef.current = stopPollingCallback; // Store cleanup in ref
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
  }, [user, currentConversationId, handleCreateConversation, pollAiResponse, messages, updateTitleFromFirstMessage, handleUpdateConversationTitle]);

  // --- Fetch Brain Config Schema ---
  const fetchBrainConfigSchema = useCallback(async () => {
    if (!user) return;
    setIsLoadingBrainConfig(true);
    setBrainConfigError(null);
    setBrainConfigSchema(null); // Clear previous schema
    try {
      const brainApiUrl = process.env.REACT_APP_BRAIN_API_URL;
      if (!brainApiUrl) {
        throw new Error("REACT_APP_BRAIN_API_URL is not defined in .env file.");
      }
      const response = await fetch(`${brainApiUrl}/get-config`);
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Failed to fetch brain config schema' }));
        throw new Error(errorData.detail || `HTTP error ${response.status}`);
      }
      const schema = await response.json();
      setBrainConfigSchema(schema);
    } catch (err: any) {
      console.error("Failed to fetch brain config schema:", err);
      setBrainConfigError(err.message || 'An unknown error occurred');
    } finally {
      setIsLoadingBrainConfig(false);
    }
  }, [user]);

  // --- Update Brain Config ---
  const updateBrainConfig = useCallback(async (newConfig: any): Promise<boolean> => {
    if (!user) {
      setSaveBrainConfigError("User not authenticated.");
      return false;
    }
    setIsSavingBrainConfig(true);
    setSaveBrainConfigError(null);
    try {
      const brainApiUrl = process.env.REACT_APP_BRAIN_API_URL;
      if (!brainApiUrl) {
        throw new Error("REACT_APP_BRAIN_API_URL is not defined in .env file.");
      }
      const response = await fetch(`${brainApiUrl}/set-config`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(newConfig),
      });

      const responseData = await response.json();

      if (!response.ok) {
        throw new Error(responseData.detail || `HTTP error ${response.status}`);
      }
      
      // Optionally, refetch the schema or update local schema if needed after save
      // For now, just indicate success. The BrainConfigView can reset its 'dirty' state.
      // await fetchBrainConfigSchema(); // Or update state based on responseData.new_config
      
      return true;
    } catch (err: any) {
      console.error("Failed to update brain config:", err);
      setSaveBrainConfigError(err.message || 'An unknown error occurred while saving configuration');
      return false;
    } finally {
      setIsSavingBrainConfig(false);
    }
  }, [user]); // Removed fetchBrainConfigSchema from deps for now

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
       if (cleanupPollingRef.current) cleanupPollingRef.current(); // Use ref for cleanup
    }
    // Cleanup polling on component unmount or when user changes
    return () => {
      if (cleanupPollingRef.current) {
          cleanupPollingRef.current();
      }
    };
  }, [user, fetchConversations]); // Removed cleanupPolling from deps

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
    handleSendMessageWithAutoConversation,
    handleCreateConversation,
    // New exports for Brain Config
    isConfigViewActive,
    setIsConfigViewActive,
    brainConfigSchema,
    isLoadingBrainConfig,
    brainConfigError,
    fetchBrainConfigSchema,
    // New exports for saving Brain Config
    isSavingBrainConfig,
    saveBrainConfigError,
    updateBrainConfig,
    // New exports for Conversation Title Update
    isUpdatingConversationTitle,
    updateConversationTitleError,
    handleUpdateConversationTitle,
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