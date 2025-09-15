import React, { useState } from 'react';
import { useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useChat } from '../../context/ChatContext';
import { getPipelineSteps, getConversationMemory } from '../../services/api';
import { PipelineStep } from '../PipelineStepsModal';

import ConversationSidebar from '../ConversationSidebar';
import ChatHeader from './ChatHeader';
import MessageList from './MessageList';
import MessageInput from './MessageInput';
import ChatModals from './ChatModals';
import FeedbackModal from '../FeedbackModal';

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
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [showFeedbackModal, setShowFeedbackModal] = useState(false);
  
  // Pipeline modal state
  const [showPipelineModal, setShowPipelineModal] = useState(false);
  const [pipelineSteps, setPipelineSteps] = useState<PipelineStep[]>([]);
  const [isLoadingSteps, setIsLoadingSteps] = useState(false);
  const [pipelineError, setPipelineError] = useState<string | null>(null);

  // Memory modal state
  const [showMemoryModal, setShowMemoryModal] = useState(false);
  const [memoryData, setMemoryData] = useState<any>(null);
  const [isLoadingMemory, setIsLoadingMemory] = useState(false);
  const [memoryError, setMemoryError] = useState<string | null>(null);

  const { user } = useAuth();
  const location = useLocation();

  // Check for debug mode
  const queryParams = new URLSearchParams(location.search);
  const isDebugMode = queryParams.get('debug') === 'true';

  React.useEffect(() => {
    if (isConfigViewActive && !brainConfigSchema && !isLoadingBrainConfig && !brainConfigError) {
      fetchBrainConfigSchema();
    }
  }, [isConfigViewActive, brainConfigSchema, isLoadingBrainConfig, brainConfigError, fetchBrainConfigSchema]);

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
    setPipelineSteps([]);

    try {
      const stepsData: PipelineStep[] = await getPipelineSteps(messageId);
      setPipelineSteps(stepsData);
      setShowPipelineModal(true);
    } catch (error: any) {
      console.error("Error fetching pipeline steps:", error);
      setPipelineError(error.message || "An unknown error occurred while fetching steps.");
      setShowPipelineModal(true);
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
    <div className="flex h-screen-mobile main-gradient-bg">
      {/* Mobile overlay */}
      {isSidebarOpen && (
        <div 
          className="sidebar-overlay"
          onClick={() => setIsSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <div className={`
        sidebar-container
        ${isSidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
      `}>
        <ConversationSidebar
          onConversationSelect={() => setIsSidebarOpen(false)}
          onOpenFeedbackModal={() => {
            setShowFeedbackModal(true);
            setIsSidebarOpen(false);
          }}
        />
      </div>
      
      <div className="flex-1 flex flex-col h-screen-mobile">
        {/* Mobile header */}
        <ChatHeader
          isSidebarOpen={isSidebarOpen}
          onToggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)}
          isDebugMode={isDebugMode}
          currentConversationId={currentConversationId}
          isConfigViewActive={isConfigViewActive}
          onViewMemory={handleViewMemory}
          isLoadingMemory={isLoadingMemory}
        />

        <main className="flex-1 p-2 sm:p-4 flex justify-center overflow-hidden relative">
          <div className="w-full max-w-4xl relative flex flex-col h-full">
            {/* Decorative elements */}
            <div className="absolute top-0 right-0 w-32 h-32 bg-yellow-200 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-blob"></div>
            <div className="absolute top-0 -left-4 w-36 h-36 bg-purple-200 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-blob animation-delay-2000"></div>
            <div className="absolute -bottom-8 left-20 w-36 h-36 bg-pink-200 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-blob animation-delay-4000"></div>
            
            {/* Messages */}
            <MessageList
              messages={messages}
              isLoadingMessages={isLoadingMessages}
              isConfigViewActive={isConfigViewActive}
              isLoadingBrainConfig={isLoadingBrainConfig}
              brainConfigSchema={brainConfigSchema}
              brainConfigError={brainConfigError}
              chatError={chatError}
              isBrainProcessing={isBrainProcessing}
              isLoadingSteps={isLoadingSteps}
              showPipelineModal={showPipelineModal}
              onViewPipelineSteps={handleViewPipelineSteps}
              mode={mode}
            />
          </div>
        </main>

        {/* Message Input */}
        <MessageInput
          newMessage={newMessage}
          setNewMessage={setNewMessage}
          onSubmit={handleFormSubmit}
          isSendingMessage={isSendingMessage}
          isConfigViewActive={isConfigViewActive}
          isLoadingMessages={isLoadingMessages}
        />
      </div>

      {/* Modals */}
      <ChatModals
        showPipelineModal={showPipelineModal}
        onClosePipelineModal={() => {
          setShowPipelineModal(false);
          setPipelineError(null);
        }}
        isLoadingSteps={isLoadingSteps}
        pipelineError={pipelineError}
        pipelineSteps={pipelineSteps}
        showMemoryModal={showMemoryModal}
        onCloseMemoryModal={() => {
          setShowMemoryModal(false);
          setMemoryError(null);
        }}
        isLoadingMemory={isLoadingMemory}
        memoryError={memoryError}
        memoryData={memoryData}
      />
      <FeedbackModal open={showFeedbackModal} onClose={() => setShowFeedbackModal(false)} />
    </div>
  );
};

export default ChatInterface;