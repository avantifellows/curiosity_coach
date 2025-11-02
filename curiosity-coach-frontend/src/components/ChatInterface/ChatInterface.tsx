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
import DebugInfo from '../DebugInfo';
import ExplorationPanel from '../ExplorationPanel';

interface ChatInterfaceProps {
  mode: 'chat' | 'test-prompt';
}

const ChatInterface: React.FC<ChatInterfaceProps> = ({ mode }) => {
  const {
    messages,
    currentConversationId,
    currentVisitNumber,
    currentPromptVersionId,
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
    preparationStatus,
    isPreparingConversation,
    isInitializingForNewUser,
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

  // Exploration panel state
  const [showExplorationPanel, setShowExplorationPanel] = useState(false);
  const [explorationDirections, setExplorationDirections] = useState<string[]>([]);
  const [explorationPrompt, setExplorationPrompt] = useState<string | undefined>(undefined);
  const lastShownAiIdRef = React.useRef<number | string | null>(null);

  const { user, logout } = useAuth();
  const location = useLocation();

  // Check for debug mode
  const queryParams = new URLSearchParams(location.search);
  const isDebugMode = queryParams.get('debug') === 'true';

  React.useEffect(() => {
    if (isConfigViewActive && !brainConfigSchema && !isLoadingBrainConfig && !brainConfigError) {
      fetchBrainConfigSchema();
    }
  }, [isConfigViewActive, brainConfigSchema, isLoadingBrainConfig, brainConfigError, fetchBrainConfigSchema]);

  // Effect to auto-load exploration directions for latest AI message in debug mode
  React.useEffect(() => {
    if (!isDebugMode || !messages || messages.length === 0) return;

    const lastAi = [...messages].reverse().find(m => !m.is_user && m.id != null);
    if (!lastAi) return;

    // avoid refetching for same message
    if (lastShownAiIdRef.current === lastAi.id) return;
    lastShownAiIdRef.current = lastAi.id as number | string;

    (async () => {
      try {
        const steps: PipelineStep[] = await getPipelineSteps(lastAi.id as number | string);
        const explorationStep = steps.find(s => s.name === 'exploration_directions_evaluation');

        if (explorationStep && Array.isArray(explorationStep.directions)) {
          setExplorationDirections(explorationStep.directions || []);
          setExplorationPrompt(explorationStep.prompt || undefined);
          setShowExplorationPanel(true);
        } else {
          // If missing, hide panel
          setExplorationDirections([]);
          setExplorationPrompt(undefined);
          setShowExplorationPanel(false);
        }
      } catch (e) {
        // On error, do not block chat; simply don't show panel
        setShowExplorationPanel(false);
      }
    })();
  }, [messages, isDebugMode]);

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

  // Determine if sidebar should be shown (only for visit 4+)
  const shouldShowSidebar = currentVisitNumber === null || currentVisitNumber >= 4;

  // Show onboarding loading screen during conversation preparation (all visits)
  if (isInitializingForNewUser || isPreparingConversation) {
    // Determine loading message based on preparation status
    let loadingMessage = "Your personal learning companion is preparing to meet you...";
    if (preparationStatus === "generating_memory") {
      loadingMessage = "Reviewing your previous conversations...";
    } else if (preparationStatus === "generating_persona") {
      loadingMessage = "Understanding your learning style...";
    }
    
    return (
      <div className="flex h-screen-mobile main-gradient-bg items-center justify-center">
        <div className="text-center p-8 max-w-md">
          {/* Animated icon */}
          <div className="mb-6 relative inline-block">
            <div className="w-20 h-20 bg-gradient-to-br from-purple-400 to-blue-500 rounded-full animate-pulse flex items-center justify-center">
              <span className="text-4xl">🌟</span>
            </div>
            <div className="absolute inset-0 w-20 h-20 bg-gradient-to-br from-purple-400 to-blue-500 rounded-full animate-ping opacity-20"></div>
          </div>
          
          {/* Loading message */}
          <h2 className="text-2xl font-bold text-gray-800 mb-3">
            Welcome to Curiosity Coach!
          </h2>
          <p className="text-lg text-gray-600 mb-2">
            {loadingMessage}
          </p>
          
          {/* Loading dots animation */}
          <div className="flex justify-center items-center space-x-2 mt-6">
            <div className="w-3 h-3 bg-purple-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
            <div className="w-3 h-3 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
            <div className="w-3 h-3 bg-pink-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen-mobile main-gradient-bg">
      {/* Mobile overlay */}
      {shouldShowSidebar && isSidebarOpen && (
        <div 
          className="sidebar-overlay"
          onClick={() => setIsSidebarOpen(false)}
        />
      )}

      {/* Sidebar - only show for visit 4+ */}
      {shouldShowSidebar && (
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
      )}
      
      {/* Main content - full width when sidebar hidden, flex-1 when sidebar shown */}
      <div className={`flex flex-col h-screen-mobile ${shouldShowSidebar ? 'flex-1' : 'w-full'}`}>
        {/* Mobile header */}
        <ChatHeader
          isSidebarOpen={isSidebarOpen}
          onToggleSidebar={shouldShowSidebar ? () => setIsSidebarOpen(!isSidebarOpen) : undefined}
          isDebugMode={isDebugMode}
          currentConversationId={currentConversationId}
          isConfigViewActive={isConfigViewActive}
          onViewMemory={handleViewMemory}
          isLoadingMemory={isLoadingMemory}
          currentVisitNumber={currentVisitNumber}
          user={user}
          onLogout={logout}
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
              preparationStatus={preparationStatus}
              isPreparingConversation={isPreparingConversation}
              isDebugMode={isDebugMode}
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
          isDisabled={isPreparingConversation || (currentConversationId !== null && messages.length === 0 && isLoadingMessages)}
          shouldShowSidebar={shouldShowSidebar}
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
      
      {/* Debug Info - only shown when ?debug=true */}
      {isDebugMode && (
        <DebugInfo 
          visitNumber={currentVisitNumber} 
          promptVersionId={currentPromptVersionId}
        />
      )}

      {/* Exploration Panel - only shown when ?debug=true */}
      <ExplorationPanel
        isOpen={showExplorationPanel}
        onClose={() => setShowExplorationPanel(false)}
        directions={explorationDirections}
        prompt={explorationPrompt}
      />

          {/* Reopen button (only in debug mode when panel is collapsed) */}
      {isDebugMode && !showExplorationPanel && (
      <button
        onClick={() => setShowExplorationPanel(true)}
        className="fixed left-2 bottom-4 z-30 bg-white border border-gray-300 shadow-md text-xs sm:text-sm px-3 py-2 rounded hover:bg-gray-50"
        title="Show exploration directions"
      >
        Show exploration directions
      </button>
    )}
    {isDebugMode && !showExplorationPanel && (
  <button
    onClick={() => setShowExplorationPanel(true)}
    className="
      fixed left-0 top-4 z-30
      bg-white border border-l-0 border-gray-300 shadow-md
      text-[11px] sm:text-xs px-2 py-2
      rounded-r hover:bg-gray-50
    "
    aria-label="Show exploration directions"
    title="Show exploration directions"
  >
    Exploration Directions
  </button>
)}
    </div>
  );
};

export default ChatInterface;