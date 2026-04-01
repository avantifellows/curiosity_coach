import React, { useRef, useEffect } from 'react';
import { CircularProgress } from '@mui/material';
import { Telegram } from '@mui/icons-material';

interface MessageInputProps {
  newMessage: string;
  setNewMessage: (message: string) => void;
  onSubmit: (e: React.FormEvent) => void;
  isSendingMessage: boolean;
  isBrainProcessing: boolean;
  isConfigViewActive: boolean;
  isLoadingMessages: boolean;
  isDisabled?: boolean;
  shouldShowSidebar?: boolean; // For conditional sidebar offset
}

const MessageInput: React.FC<MessageInputProps> = ({
  newMessage,
  setNewMessage,
  onSubmit,
  isSendingMessage,
  isBrainProcessing,
  isConfigViewActive,
  isLoadingMessages,
  isDisabled = false,
  shouldShowSidebar = true,
}) => {
  const isWaitingForResponse = isSendingMessage || isBrainProcessing;
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-focus the textarea when ready for input
  useEffect(() => {
    if (
      !isConfigViewActive && 
      !isWaitingForResponse && 
      !isLoadingMessages && 
      textareaRef.current
    ) {
      // Small delay to ensure everything is rendered
      setTimeout(() => {
        textareaRef.current?.focus();
      }, 100);
    }
  }, [isConfigViewActive, isWaitingForResponse, isLoadingMessages]);

  if (isConfigViewActive) {
    return null;
  }

  // Conditionally apply sidebar offset only when sidebar is shown
  const sidebarOffsetClass = shouldShowSidebar ? 'lg:left-72' : 'left-0';

  return (
    <div className={`fixed bottom-0 right-0 z-50 ${sidebarOffsetClass}`}>
      <div className="floating-input-bg">
        <div className="w-full max-w-4xl">
          <form onSubmit={onSubmit} className="flex items-center space-x-3">
            <textarea
              ref={textareaRef}
              className="floating-input"
              rows={1}
              placeholder={
                isWaitingForResponse
                  ? 'Curiosity Coach is replying...'
                  : 'Ask about homework, class, or anything you want to understand better'
              }
              value={newMessage}
              onChange={(e) => setNewMessage(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  if (!isWaitingForResponse && !isDisabled) {
                    onSubmit(e);
                  }
                }
              }}
              disabled={isDisabled}
            />
            <button
              type="submit"
              className={`btn-gradient-primary ${isWaitingForResponse ? 'animate-pulse' : ''}`}
              disabled={!newMessage.trim() || isWaitingForResponse || isDisabled}
            >
              {isWaitingForResponse ? (
                  <CircularProgress size={24} color="inherit" />
              ) : (
                  <Telegram fontSize="medium" />
              )}
            </button>
          </form>
          <div className="mt-2 flex items-center justify-between px-1 text-[11px] text-slate-500 sm:text-xs">
            <span>Press Enter to send. Shift+Enter adds a new line.</span>
            <span className="hidden sm:inline">Stay curious. Keep digging ✦</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MessageInput;
