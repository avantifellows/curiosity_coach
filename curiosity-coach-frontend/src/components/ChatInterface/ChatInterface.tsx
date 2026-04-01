import React, { useState } from 'react';
import { useLocation } from 'react-router-dom';
import { CircularProgress } from '@mui/material';
import { AutoAwesomeRounded } from '@mui/icons-material';
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
import CuriosityScoreIndicator from '../common/CuriosityScoreIndicator';

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
  const [curiosityTip, setCuriosityTip] = useState<string | undefined>(undefined);
  const lastShownAiIdRef = React.useRef<number | string | null>(null);
  const lastTipFetchedAiIdRef = React.useRef<number | string | null>(null);

  const { user, logout } = useAuth();
  const location = useLocation();

  const curiosityScore = React.useMemo(() => {
    if (!messages || messages.length === 0) return 0;
    return messages.reduce((maxScore, message) => {
      if (!message.is_user && typeof message.curiosity_score === 'number') {
        return Math.max(maxScore, message.curiosity_score);
      }
      return maxScore;
    }, 0);
  }, [messages]);

  // Check for debug mode
  const queryParams = new URLSearchParams(location.search);
  const isDebugMode = queryParams.get('debug') === 'true';

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
          // Also update the tip in debug mode
          setCuriosityTip(explorationStep.curiosity_tip || undefined);
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

  // Effect to fetch curiosity tip for the score indicator (non-debug mode)
  React.useEffect(() => {
    if (isDebugMode || !messages || messages.length === 0) return;

    const lastAi = [...messages].reverse().find(m => !m.is_user && m.id != null);
    if (!lastAi) return;

    // avoid refetching for same message
    if (lastTipFetchedAiIdRef.current === lastAi.id) return;
    lastTipFetchedAiIdRef.current = lastAi.id as number | string;

    (async () => {
      try {
        const steps: PipelineStep[] = await getPipelineSteps(lastAi.id as number | string);
        const explorationStep = steps.find(s => s.name === 'exploration_directions_evaluation');

        if (explorationStep?.curiosity_tip) {
          setCuriosityTip(explorationStep.curiosity_tip);
        }
      } catch (e) {
        // On error, don't update the tip - fallback will be used
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

  // Calculate total processing time from steps (sum of all time_taken values)
  const totalProcessingTime = React.useMemo(() => {
    if (!pipelineSteps || pipelineSteps.length === 0) return null;
    const total = pipelineSteps.reduce((sum, step) => {
      if (step.time_taken !== null && step.time_taken !== undefined) {
        return sum + step.time_taken;
      }
      return sum;
    }, 0);
    return total > 0 ? total : null;
  }, [pipelineSteps]);

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

  // Sidebar disabled for all visits
  const shouldShowSidebar = false;

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
      <div className="flex h-screen-mobile main-gradient-bg items-center justify-center px-6">
        <div className="w-full max-w-md rounded-3xl border border-violet-200 bg-white/95 p-8 text-center shadow-sm">
          <div className="mb-4 inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-violet-100 text-violet-700 animate-twinkle">
            <AutoAwesomeRounded />
          </div>
          <div className="mb-6 flex justify-center">
            <CircularProgress size={24} sx={{ color: '#7c3aed' }} />
          </div>

          <h2 className="mb-3 text-2xl font-semibold text-slate-900">
            Welcome to Curiosity Coach!
          </h2>
          <p className="mb-2 text-base text-slate-600 sm:text-lg">
            {loadingMessage}
          </p>
          <div className="mt-4 text-sm text-violet-700">
            We’re getting your coach ready for a thoughtful first conversation.
          </div>
          <div className="mt-2 text-sm text-slate-500">
            This can take a minute or two the first time.
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
            {/* Messages */}
            <MessageList
              messages={messages}
              isLoadingMessages={isLoadingMessages}
              isConfigViewActive={isConfigViewActive}
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
          isBrainProcessing={isBrainProcessing}
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
        isDebugMode={isDebugMode}
        totalProcessingTime={totalProcessingTime}
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
          curiosityScore={curiosityScore}
        />
      )}

      {!isDebugMode && messages.length > 0 && (
        <CuriosityScoreIndicator score={curiosityScore} tip={curiosityTip} />
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
