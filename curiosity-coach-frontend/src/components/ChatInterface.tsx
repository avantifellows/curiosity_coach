import React, { useState, useEffect, useRef } from 'react';
import { CircularProgress } from '@mui/material';
import ChatMessage from './ChatMessage';
import ConversationSidebar from './ConversationSidebar';
import BrainConfigView from './BrainConfigView';
import { useChat } from '../context/ChatContext';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { LogoutOutlined, Send, Visibility, Menu, Close } from '@mui/icons-material';
import { getPipelineSteps } from '../services/api';
import PipelineStepsModal, { PipelineStep } from './PipelineStepsModal';

const ChatInterface: React.FC = () => {
  const {
    messages,
    currentConversationId,
    isLoadingMessages,
    isSendingMessage,
    error: chatError,
    handleSendMessage: handleSendMessageContext,
    selectConversation,
    isBrainProcessing,
    isConfigViewActive,
    brainConfigSchema,
    isLoadingBrainConfig,
    brainConfigError,
    fetchBrainConfigSchema,
    handleCreateConversation,
    conversations,
    isLoadingConversations,
  } = useChat();

  const [newMessage, setNewMessage] = useState('');
  const [showPipelineModal, setShowPipelineModal] = useState(false);
  const [pipelineSteps, setPipelineSteps] = useState<PipelineStep[]>([]);
  const [isLoadingSteps, setIsLoadingSteps] = useState(false);
  const [pipelineError, setPipelineError] = useState<string | null>(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [hasAutoStarted, setHasAutoStarted] = useState(false);

  const { user, logout } = useAuth();

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const navigate = useNavigate();

  useEffect(() => {
    if (!isConfigViewActive) {
      setTimeout(() => {
          messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
      }, 100); 
    }
  }, [messages, isConfigViewActive]);

  useEffect(() => {
    if (isConfigViewActive && !brainConfigSchema && !isLoadingBrainConfig && !brainConfigError) {
      fetchBrainConfigSchema();
    }
  }, [isConfigViewActive, brainConfigSchema, isLoadingBrainConfig, brainConfigError, fetchBrainConfigSchema]);

  // Auto-start a new chat when the component loads and no conversation is selected
  useEffect(() => {
    if (
      user && 
      !hasAutoStarted && 
      !isLoadingConversations && 
      currentConversationId === null && 
      !isConfigViewActive
    ) {
      const existingConversations = conversations.length;
      const newChatTitle = `newchat_${existingConversations + 1}`;
      handleCreateConversation(newChatTitle);
      setHasAutoStarted(true);
    }
  }, [user, hasAutoStarted, isLoadingConversations, currentConversationId, isConfigViewActive, conversations.length, handleCreateConversation]);

  // Auto-focus the textarea when ready for input
  useEffect(() => {
    if (
      !isConfigViewActive && 
      !isSendingMessage && 
      !isLoadingMessages && 
      currentConversationId !== null &&
      textareaRef.current
    ) {
      // Small delay to ensure everything is rendered
      setTimeout(() => {
        textareaRef.current?.focus();
      }, 100);
    }
  }, [isConfigViewActive, isSendingMessage, isLoadingMessages, currentConversationId]);

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

  const handleViewPipelineSteps = async (messageId: number | string) => {
    if (!messageId) return;
    console.log("Fetching pipeline steps for message ID:", messageId);
    setIsLoadingSteps(true);
    setPipelineError(null);
    setPipelineSteps([]); // Clear previous steps

    try {
      const stepsData: PipelineStep[] = await getPipelineSteps(messageId);
      console.log("Fetched steps:", stepsData);
      setPipelineSteps(stepsData);
      setShowPipelineModal(true);
    } catch (error: any) {
      console.error("Error fetching pipeline steps:", error);
      setPipelineError(error.message || "An unknown error occurred while fetching steps.");
      setShowPipelineModal(true); // Still show modal to display the error
    } finally {
      setIsLoadingSteps(false);
    }
  };

  return (
    <div className="flex h-screen bg-gray-100">
      {/* Mobile overlay */}
      {isSidebarOpen && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-50 z-40 lg:hidden"
          onClick={() => setIsSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <div className={`
        ${isSidebarOpen ? 'translate-x-0' : '-translate-x-full'} 
        lg:translate-x-0 
        fixed lg:static 
        inset-y-0 left-0 
        z-50 lg:z-auto
        w-64 
        transition-transform duration-300 ease-in-out
        lg:transition-none
      `}>
        <ConversationSidebar onConversationSelect={() => setIsSidebarOpen(false)} />
      </div>
      
      <div className="flex-1 flex flex-col h-screen lg:ml-0">
        <header className="bg-white shadow-xs border-b border-gray-200">
          <div className="px-6 py-3 flex justify-between items-center">
            <div className="flex items-center">
              {/* Hamburger menu button */}
              <button
                onClick={() => setIsSidebarOpen(!isSidebarOpen)}
                className="lg:hidden mr-3 p-2 rounded-md text-gray-600 hover:text-gray-800 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                aria-label="Toggle sidebar"
              >
                {isSidebarOpen ? <Close /> : <Menu />}
              </button>
              
              <div>
                <h2 className="text-lg font-semibold text-gray-800">
                  {isConfigViewActive ? 'Brain Configuration' : (currentConversationId ? `Chat` : 'Curiosity Coach')}
                </h2>
                {user && !isConfigViewActive && (
                  <p className="text-xs text-gray-500">
                    Logged in as: {user.phone_number}
                  </p>
                )}
              </div>
            </div>
            <div className="flex items-center space-x-3">
              <button 
                onClick={handleLogout}
                className="flex items-center px-3 py-1.5 bg-red-500 text-white rounded hover:bg-red-600 transition duration-150 ease-in-out text-sm"
                title="Logout"
              >
                <LogoutOutlined fontSize="small" className="mr-1"/> 
                Logout
              </button>
            </div>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50">
          {isConfigViewActive ? (
            <BrainConfigView 
              isLoadingBrainConfig={isLoadingBrainConfig}
              brainConfigSchema={brainConfigSchema}
              brainConfigError={brainConfigError}
            />
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
              <React.Fragment key={msg.id || `msg-${index}`}>
                <ChatMessage message={msg} />
                {!msg.is_user && msg.id && !isConfigViewActive && ( // Only show "View thinking steps" when not in config view
                  <div className="flex justify-start pl-10 -mt-2 mb-2">
                    <button
                      onClick={() => handleViewPipelineSteps(msg.id!)}
                      className="text-xs text-indigo-600 hover:text-indigo-800 hover:underline focus:outline-none flex items-center"
                      disabled={isLoadingSteps}
                    >
                      <Visibility fontSize="inherit" className="mr-1" />
                      {isLoadingSteps && showPipelineModal ? 'Loading steps...' : 'View thinking steps'}
                    </button>
                  </div>
                )}
              </React.Fragment>
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

        {!isConfigViewActive && (
          <footer className="bg-white p-4 border-t border-gray-200">
            <form onSubmit={handleFormSubmit} className="flex items-center space-x-3">
              <textarea
                ref={textareaRef}
                className="flex-1 resize-none border rounded-md p-2 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
                rows={1}
                placeholder="Type your message..."
                value={newMessage}
                onChange={(e) => setNewMessage(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleFormSubmit(e);
                  }
                }}
                disabled={isSendingMessage}
              />
              <button
                type="submit"
                className={`px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed ${isSendingMessage ? 'animate-pulse' : ''}`}
                disabled={!newMessage.trim() || isSendingMessage}
              >
                {isSendingMessage ? (
                    <CircularProgress size={20} color="inherit" />
                ) : (
                    <Send fontSize="small" />
                )}
              </button>
            </form>
          </footer>
        )}
      </div>

      {/* Use the new PipelineStepsModal component */}
      <PipelineStepsModal 
        showModal={showPipelineModal}
        onClose={() => {
          setShowPipelineModal(false);
          setPipelineError(null); // Clear error when closing
        }}
        isLoading={isLoadingSteps}
        error={pipelineError}
        steps={pipelineSteps}
      />
    </div>
  );
};

export default ChatInterface; 