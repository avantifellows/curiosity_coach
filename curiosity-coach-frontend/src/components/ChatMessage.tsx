import React from 'react';
// import { Message } from '../types';

interface DisplayMessageForChat {
  id: number | string;
  content: string;
  sender: 'user' | 'ai';
  timestamp: string;
  status?: 'sending' | 'sent' | 'failed';
  user_id?: number;
}

interface ChatMessageProps {
  message: DisplayMessageForChat;
}

const ChatMessage: React.FC<ChatMessageProps> = ({ message }) => {
  const isUser = message.sender === 'user';
  
  const bubbleClass = isUser ? 'chat-bubble-user' : 'chat-bubble-bot';
  
  const statusOpacity = message.status === 'sending' || message.status === 'failed' ? 'opacity-60' : '';
  
  return (
    <div className={`mb-4 flex ${isUser ? 'justify-end' : 'justify-start'} ${statusOpacity}`}>
      <div className={bubbleClass}>
        <p className="whitespace-pre-wrap break-words">{message.content}</p>
        {message.status === 'sending' && 
          <p className="text-xs opacity-70 text-right mt-1 italic">Sending...</p>
        }
        {message.status === 'failed' && 
          <p className="text-xs text-red-500 opacity-90 text-right mt-1">Failed</p>
        }
        {message.timestamp && message.status !== 'sending' && message.status !== 'failed' && (
          <p className="text-xs opacity-70 text-right mt-1">
            {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </p>
        )}
      </div>
    </div>
  );
};

export default ChatMessage; 