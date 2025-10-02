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
  isLoadingBrainConfig: boolean;
  brainConfigSchema: any;
  brainConfigError: string | null;
  chatError: string | null;
  isBrainProcessing: boolean;
  isLoadingSteps: boolean;
  showPipelineModal: boolean;
  onViewPipelineSteps: (messageId: number | string) => void;
  mode: 'chat' | 'test-prompt';
}

const MessageList: React.FC<MessageListProps> = ({
  messages,
  isLoadingMessages,
  isConfigViewActive,
  isLoadingBrainConfig,
  brainConfigSchema,
  brainConfigError,
  chatError,
  isBrainProcessing,
  isLoadingSteps,
  showPipelineModal,
  onViewPipelineSteps,
  mode,
}) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to latest message when messages load or new messages arrive
  useEffect(() => {
    if (messages.length > 0 && messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  return (
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
            <div className="card-gradient">
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
                {!msg.is_user && msg.id && !isConfigViewActive && mode === 'test-prompt' && (
                  <div className="flex justify-start pl-2 mt-1">
                    <button
                      onClick={() => onViewPipelineSteps(msg.id as number | string)}
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
          <div className="text-center text-red-500 bg-red-100 p-2 rounded mx-2">
            Error: {chatError}
          </div>
        )}
        
        {isBrainProcessing && (
          <div className="flex justify-start pl-2">
            <div className="thinking-bubble">
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
  );
};

export default MessageList;