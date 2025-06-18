import React, { useState, useEffect, useRef } from 'react';
import { CircularProgress } from '@mui/material';
import ChatMessage from './ChatMessage';
import ConversationSidebar from './ConversationSidebar';
import BrainConfigView from './BrainConfigView';
import { useChat } from '../context/ChatContext';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { LogoutOutlined, Send, Visibility, Menu, Close, Psychology } from '@mui/icons-material';
import { getPipelineSteps, getConversationMemory } from '../services/api';
import PipelineStepsModal, { PipelineStep } from './PipelineStepsModal';
import MemoryViewModal from './MemoryViewModal';

interface ChatInterfaceProps {
  mode: 'chat' | 'test-prompt';
}

const ChatInterface: React.FC<ChatInterfaceProps> = ({ mode }) => {
  const {
    messages,
    currentConversationId,
    isLoadingMessages,
    isSendingMessage,
    error: chatError,
    handleSendMessageWithAutoConversation,
    selectConversation,
    isBrainProcessing,
    isConfigViewActive,
    brainConfigSchema,
    isLoadingBrainConfig,
    brainConfigError,
    fetchBrainConfigSchema,
  } = useChat();

  const [newMessage, setNewMessage] = useState('');
  const [showPipelineModal, setShowPipelineModal] = useState(false);
  const [pipelineSteps, setPipelineSteps] = useState<PipelineStep[]>([]);
  const [isLoadingSteps, setIsLoadingSteps] = useState(false);
  const [pipelineError, setPipelineError] = useState<string | null>(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  // State for memory view
  const [showMemoryModal, setShowMemoryModal] = useState(false);
  const [memoryData, setMemoryData] = useState<any>(null);
  const [isLoadingMemory, setIsLoadingMemory] = useState(false);
  const [memoryError, setMemoryError] = useState<string | null>(null);

  const { user, logout } = useAuth();

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const navigate = useNavigate();
  const location = useLocation();

  // Check for debug mode
  const queryParams = new URLSearchParams(location.search);
  const isDebugMode = queryParams.get('debug') === 'true';

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

  // Auto-focus the textarea when ready for input
  useEffect(() => {
    if (
      !isConfigViewActive && 
      !isSendingMessage && 
      !isLoadingMessages && 
      textareaRef.current
    ) {
      // Small delay to ensure everything is rendered
      setTimeout(() => {
        textareaRef.current?.focus();
      }, 100);
    }
  }, [isConfigViewActive, isSendingMessage, isLoadingMessages]);

  const handleFormSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newMessage.trim() || !user || isSendingMessage) return;

    const contentToSend = newMessage.trim();
    setNewMessage('');

    await handleSendMessageWithAutoConversation(contentToSend, mode);
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

  const handleViewMemory = async () => {
    if (!currentConversationId) return;
    setIsLoadingMemory(true);
    setMemoryError(null);
    setMemoryData(null);

    try {
      const data = await getConversationMemory(currentConversationId);
      setMemoryData(data);
    } catch (error: any) {
      setMemoryError(error.message || "An unknown error occurred while fetching memory.");
    } finally {
      setIsLoadingMemory(false);
      setShowMemoryModal(true);
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
          <div className="px-4 sm:px-6 py-3 flex justify-between items-center">
            <div className="flex items-center min-w-0 flex-1">
              {/* Hamburger menu button */}
              <button
                onClick={() => setIsSidebarOpen(!isSidebarOpen)}
                className="lg:hidden mr-3 p-2 rounded-md text-gray-600 hover:text-gray-800 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-indigo-500 flex-shrink-0"
                aria-label="Toggle sidebar"
              >
                {isSidebarOpen ? <Close /> : <Menu />}
              </button>
              
              <div className="min-w-0 flex-1">
                <h2 className="text-lg font-semibold text-gray-800 truncate">
                  {getHeaderTitle()}
                </h2>
                {user && !isConfigViewActive && (
                  <p className="text-xs text-gray-500 hidden sm:block truncate">
                    Logged in as: {user.phone_number}
                  </p>
                )}
              </div>
            </div>
            <div className="flex items-center space-x-2 sm:space-x-3 flex-shrink-0">
              {isDebugMode && currentConversationId && !isConfigViewActive && (
                <button
                  onClick={handleViewMemory}
                  className="flex items-center px-2 sm:px-3 py-1.5 bg-blue-500 text-white rounded hover:bg-blue-600 transition duration-150 ease-in-out text-sm"
                  title="See AI Generated Memory for this conversation"
                  disabled={isLoadingMemory}
                >
                  <Psychology fontSize="small" className="mr-0 sm:mr-1"/>
                  <span className="hidden sm:inline">
                    {isLoadingMemory ? 'Loading...' : 'See Memory'}
                  </span>
                </button>
              )}
              <button 
                onClick={handleLogout}
                className="flex items-center px-2 sm:px-3 py-1.5 bg-red-500 text-white rounded hover:bg-red-600 transition duration-150 ease-in-out text-sm"
                title="Logout"
              >
                <LogoutOutlined fontSize="small" className="mr-0 sm:mr-1"/> 
                <span className="hidden sm:inline">Logout</span>
              </button>
            </div>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto p-2 sm:p-4 space-y-4 bg-gray-50">
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
              <p className="text-gray-500 text-center px-4">Send a message to start chatting!</p>
            </div>
          ) : (
            messages.map((msg, index) => (
              <React.Fragment key={msg.id || `msg-${index}`}>
                <ChatMessage message={msg} />
                {!msg.is_user && msg.id && !isConfigViewActive && ( // Only show "View thinking steps" when not in config view
                  <div className="flex justify-start pl-4 sm:pl-10 -mt-2 mb-2">
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
            <div className="text-center text-red-500 bg-red-100 p-2 rounded mx-2">Error: {chatError}</div>
          )}
          {isBrainProcessing && (
            <div className="flex justify-start pl-2">
                <div className="bg-gray-200 text-gray-700 rounded-lg px-4 py-2 max-w-[85%] sm:max-w-xs lg:max-w-md shadow animate-pulse">
                  Thinking...
                </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </main>

        {!isConfigViewActive && (
          <footer className="bg-white p-2 sm:p-4 border-t border-gray-200">
            <form onSubmit={handleFormSubmit} className="flex items-end space-x-2 sm:space-x-3">
              <textarea
                ref={textareaRef}
                className="flex-1 resize-none border rounded-md p-2 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed text-sm sm:text-base min-h-[2.5rem] max-h-32"
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
                className={`p-2 sm:px-4 sm:py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed flex-shrink-0 ${isSendingMessage ? 'animate-pulse' : ''}`}
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

      {/* Memory View Modal */}
      <MemoryViewModal
        showModal={showMemoryModal}
        onClose={() => {
          setShowMemoryModal(false);
          setMemoryError(null);
        }}
        isLoading={isLoadingMemory}
        error={memoryError}
        memoryData={memoryData}
      />
    </div>
  );
};

export default ChatInterface; 