import React, { useState, useEffect, useRef } from 'react';
import { CircularProgress } from '@mui/material';
import ChatMessage from './ChatMessage';
import ConversationSidebar from './ConversationSidebar';
import BrainConfigView from './BrainConfigView';
import { useChat } from '../context/ChatContext';
import { useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Visibility, Menu, Close, Psychology, Telegram } from '@mui/icons-material';
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

  const { user } = useAuth();

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const location = useLocation();

  // Check for debug mode
  const queryParams = new URLSearchParams(location.search);
  const isDebugMode = queryParams.get('debug') === 'true';

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

  // Auto-scroll to latest message when messages load or new messages arrive
  useEffect(() => {
    if (messages.length > 0 && messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  const handleFormSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newMessage.trim() || !user || isSendingMessage) return;

    const contentToSend = newMessage.trim();
    setNewMessage('');

    await handleSendMessageWithAutoConversation(contentToSend, mode);
  };

  const handleViewPipelineSteps = async (messageId: number | string) => {
    if (!messageId) return;
    setIsLoadingSteps(true);
    setPipelineError(null);
    setPipelineSteps([]); // Clear previous steps

    try {
      const stepsData: PipelineStep[] = await getPipelineSteps(messageId);
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
    <div className="flex h-screen-mobile bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50">
      {/* Mobile overlay */}
      {isSidebarOpen && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-50 z-30 lg:hidden"
          onClick={() => setIsSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <div className={`
        ${isSidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'} 
        fixed lg:static 
        inset-y-0 left-0 
        z-50 lg:z-auto
        w-72 
        transition-transform duration-300 ease-in-out
        lg:transition-none
      `}>
        <ConversationSidebar onConversationSelect={() => setIsSidebarOpen(false)} />
      </div>
      
      <div className="flex-1 flex flex-col h-screen-mobile">
        {/* Mobile hamburger menu button */}
        <div className="lg:hidden p-3 bg-gradient-to-r from-indigo-500 to-purple-500 shadow-lg flex items-center justify-between z-40 relative">
          <button
            onClick={() => setIsSidebarOpen(!isSidebarOpen)}
            className="p-3 rounded-xl bg-white bg-opacity-20 backdrop-blur-sm text-white hover:bg-opacity-30 focus:outline-none focus:ring-2 focus:ring-white focus:ring-opacity-50 flex items-center justify-center transition-all duration-200 hover:scale-105"
            aria-label="Toggle sidebar"
          >
            {isSidebarOpen ? <Close fontSize="medium" /> : <Menu fontSize="medium" />}
          </button>
          
          <div className="flex items-center space-x-2">
            <span className="text-white font-medium text-lg">Curiosity Coach</span>
            <span className="text-2xl">🤔</span>
          </div>
          
          {isDebugMode && currentConversationId && !isConfigViewActive && (
            <button
              onClick={handleViewMemory}
              className="flex items-center px-3 py-2 bg-white bg-opacity-20 backdrop-blur-sm text-white rounded-xl hover:bg-opacity-30 transition-all duration-200 hover:scale-105 text-sm"
              title="See AI Generated Memory for this conversation"
              disabled={isLoadingMemory}
            >
              <Psychology fontSize="small" className="mr-1"/>
              <span className="hidden sm:inline">
                {isLoadingMemory ? 'Loading...' : 'Memory'}
              </span>
            </button>
          )}
        </div>

        <main className="flex-1 p-2 sm:p-4 flex justify-center overflow-hidden relative">
          <div className="w-full max-w-4xl relative flex flex-col h-full">
            {/* Decorative elements - subtle and non-distracting */}
            <div className="absolute top-0 right-0 w-32 h-32 bg-yellow-200 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-blob"></div>
            <div className="absolute top-0 -left-4 w-36 h-36 bg-purple-200 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-blob animation-delay-2000"></div>
            <div className="absolute -bottom-8 left-20 w-36 h-36 bg-pink-200 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-blob animation-delay-4000"></div>
            
            {/* Content container with higher z-index and bottom padding for floating input */}
            <div className="relative z-10 flex flex-col flex-1 overflow-y-auto custom-scrollbar pb-32">
              
              {/* Empty space pusher for when there are few messages */}
              {messages.length > 0 && messages.length < 4 && (
                <div className="flex-1"></div>
              )}
              
              {/* Messages container */}
              <div className="flex flex-col">
            
              {isConfigViewActive ? (
                <BrainConfigView 
                  isLoadingBrainConfig={isLoadingBrainConfig}
                  brainConfigSchema={brainConfigSchema}
                  brainConfigError={brainConfigError}
                />
              ) : isLoadingMessages ? (
                <div className="flex justify-center items-center h-full py-20">
                  <CircularProgress />
                </div>
              ) : messages.length === 0 ? (
                <div className="flex justify-center items-center flex-1 py-20">
                  <div className="bg-gradient-to-r from-indigo-100 to-purple-100 p-6 rounded-xl shadow-md transform transition-all duration-300 hover:scale-105 hover:shadow-lg backdrop-filter backdrop-blur-sm bg-opacity-90">
                    <h2 className="text-2xl md:text-3xl font-bold text-indigo-600 text-center">
                      What are you curious about today? <span className="inline-block animate-bounce">🤔</span>
                    </h2>
                  </div>
                </div>
              ) : (
                <div className="py-4 flex flex-col">
                  {messages.map((msg, index) => (
                    <div key={msg.id || `msg-${index}`} className="mb-6">
                      <ChatMessage message={msg} />
                      {!msg.is_user && msg.id && !isConfigViewActive && (
                        <div className="flex justify-start pl-2 mt-1">
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
                    </div>
                  ))}
                </div>
              )}
              {chatError && (
                <div className="text-center text-red-500 bg-red-100 p-2 rounded mx-2">Error: {chatError}</div>
              )}
              {isBrainProcessing && (
                <div className="flex justify-start pl-2">
                  <div className="flex items-center bg-gradient-to-r from-gray-100 to-blue-100 text-gray-700 rounded-lg px-4 py-2 max-w-[85%] sm:max-w-xs lg:max-w-md shadow backdrop-filter backdrop-blur-sm bg-opacity-90">
                    <div className="mr-2">
                      <div className="animate-pulse flex space-x-1">
                        <div className="h-2 w-2 bg-blue-400 rounded-full"></div>
                        <div className="h-2 w-2 bg-blue-400 rounded-full"></div>
                        <div className="h-2 w-2 bg-blue-400 rounded-full"></div>
                      </div>
                    </div>
                    Thinking...
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
              </div>
            </div>
          </div>
        </main>

        {/* Floating input box */}
        {!isConfigViewActive && (
          <div className="fixed bottom-0 left-0 right-0 z-50 lg:left-72">
            <div className="p-3 sm:p-6 flex justify-center bg-gradient-to-t from-white via-white to-transparent">
              <form onSubmit={handleFormSubmit} className="flex items-center space-x-3 w-full max-w-4xl">
                <textarea
                  ref={textareaRef}
                  className="flex-1 resize-none border-2 border-indigo-200 rounded-2xl p-4 bg-white focus:outline-none focus:ring-3 focus:ring-indigo-300 focus:border-indigo-400 disabled:opacity-50 disabled:cursor-not-allowed text-base min-h-[3rem] max-h-32 shadow-xl placeholder-gray-400 backdrop-blur-sm"
                  rows={1}
                  placeholder=""
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
                  className={`px-5 py-4 bg-gradient-to-r from-indigo-500 to-purple-500 text-white rounded-2xl hover:from-indigo-600 hover:to-purple-600 focus:outline-none focus:ring-3 focus:ring-indigo-300 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed flex-shrink-0 h-12 flex items-center justify-center transition-all duration-200 hover:scale-105 shadow-xl font-medium ${isSendingMessage ? 'animate-pulse' : ''}`}
                  disabled={!newMessage.trim() || isSendingMessage}
                >
                  {isSendingMessage ? (
                      <CircularProgress size={24} color="inherit" />
                  ) : (
                      <Telegram fontSize="medium" />
                  )}
                </button>
              </form>
            </div>
          </div>
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