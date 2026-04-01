import React, { useRef, useEffect } from 'react';
import { CircularProgress } from '@mui/material';
import { Visibility } from '@mui/icons-material';
import ChatMessage from '../ChatMessage';
import BrainConfigView from '../BrainConfigView';

import { Message } from '../../types';

interface MessageListProps {
  messages: Message[];
  isLoadingMessages: boolean;
  isConfigViewActive: boolean;
  chatError: string | null;
  isBrainProcessing: boolean;
  isLoadingSteps: boolean;
  showPipelineModal: boolean;
  onViewPipelineSteps: (messageId: number | string) => void;
  mode: 'chat' | 'test-prompt';
  preparationStatus?: string | null;
  isPreparingConversation?: boolean;
  isDebugMode?: boolean;
}

const MessageList: React.FC<MessageListProps> = ({
  messages,
  isLoadingMessages,
  isConfigViewActive,
  chatError,
  isBrainProcessing,
  isLoadingSteps,
  showPipelineModal,
  onViewPipelineSteps,
  mode,
  preparationStatus,
  isPreparingConversation,
  isDebugMode = false,
}) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to latest message when messages load or new messages arrive
  useEffect(() => {
    if (messages.length > 0 && messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  return (
    <div className="relative z-10 flex flex-col flex-1 overflow-y-auto custom-scrollbar pb-40">
      {/* Empty space pusher for when there are few messages */}
      {messages.length > 0 && messages.length < 4 && (
        <div className="flex-1"></div>
      )}
      
      {/* Messages container */}
      <div className="flex flex-col">
        {isConfigViewActive ? (
          <BrainConfigView />
        ) : isLoadingMessages ? (
          <div className="flex justify-center items-center h-full py-20">
            <CircularProgress />
          </div>
        ) : isPreparingConversation && preparationStatus ? (
          <div className="flex justify-center items-center flex-1 py-20">
            <div className="card-gradient">
              <div className="flex flex-col items-center">
                <div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-violet-100 text-xl text-violet-700 animate-twinkle">
                  ✦
                </div>
                <CircularProgress size={40} className="mb-4" />
                <h2 className="text-xl md:text-2xl font-semibold text-slate-900 text-center">
                  {preparationStatus === 'generating_memory' && 'Reviewing your previous conversations...'}
                  {preparationStatus === 'generating_persona' && 'Understanding your learning style...'}
                  {preparationStatus === 'ready' && 'Your coach is preparing to meet you...'}
                </h2>
                <p className="mt-2 text-sm text-slate-500">This may take up to 2 minutes</p>
              </div>
            </div>
          </div>
        ) : messages.length === 0 ? (
          <div className="flex justify-center items-center flex-1 py-20">
            <div className="card-gradient">
              <div className="mb-4 flex justify-center">
                <span className="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-violet-100 text-xl text-violet-700">
                  ✦
                </span>
              </div>
              <h2 className="text-2xl md:text-3xl font-semibold text-slate-900 text-center">
                Ask about class, homework, or anything you want to understand better.
              </h2>
              <p className="mt-3 text-center text-sm text-slate-500">
                Short questions are fine. You can also paste a longer problem.
              </p>
              <p className="mt-2 text-center text-sm text-violet-700">
                Start with one thing that feels confusing, interesting, or unfinished.
              </p>
            </div>
          </div>
        ) : (
          <div className="py-4 flex flex-col">
            {messages.map((msg, index) => (
              <div key={msg.id || `msg-${index}`} className="mb-6">
                <ChatMessage message={msg} />
                {!msg.is_user && msg.id && !isConfigViewActive && (mode === 'test-prompt' || isDebugMode) && (
                  <div className="flex justify-start pl-2 mt-1">
                    <button
                      onClick={() => onViewPipelineSteps(msg.id as number | string)}
                      className="flex items-center text-xs text-violet-600 hover:text-violet-700 hover:underline focus:outline-none"
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
          <div className="text-center text-red-500 bg-red-100 p-2 rounded mx-2">
            Error: {chatError}
          </div>
        )}
        
        {isBrainProcessing && (
          <div className="flex justify-start pl-2">
            <div className="thinking-bubble">
              <div className="mr-2">
                <div className="animate-pulse flex space-x-1">
                  <div className="h-2 w-2 bg-violet-500 rounded-full"></div>
                  <div className="h-2 w-2 bg-fuchsia-400 rounded-full"></div>
                  <div className="h-2 w-2 bg-indigo-400 rounded-full"></div>
                </div>
              </div>
              Thinking...
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>
    </div>
  );
};

export default MessageList;
