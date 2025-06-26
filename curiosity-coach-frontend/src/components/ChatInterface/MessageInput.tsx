import React, { useRef, useEffect } from 'react';
import { CircularProgress } from '@mui/material';
import { Telegram } from '@mui/icons-material';

interface MessageInputProps {
  newMessage: string;
  setNewMessage: (message: string) => void;
  onSubmit: (e: React.FormEvent) => void;
  isSendingMessage: boolean;
  isConfigViewActive: boolean;
  isLoadingMessages: boolean;
}

const MessageInput: React.FC<MessageInputProps> = ({
  newMessage,
  setNewMessage,
  onSubmit,
  isSendingMessage,
  isConfigViewActive,
  isLoadingMessages,
}) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

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

  if (isConfigViewActive) {
    return null;
  }

  return (
    <div className="floating-input-container">
      <div className="floating-input-bg">
        <form onSubmit={onSubmit} className="flex items-center space-x-3 w-full max-w-4xl">
          <textarea
            ref={textareaRef}
            className="floating-input"
            rows={1}
            placeholder=""
            value={newMessage}
            onChange={(e) => setNewMessage(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                onSubmit(e);
              }
            }}
            disabled={isSendingMessage}
          />
          <button
            type="submit"
            className={`btn-gradient-primary ${isSendingMessage ? 'animate-pulse' : ''}`}
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
  );
};

export default MessageInput;