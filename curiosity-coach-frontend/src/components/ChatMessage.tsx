import React from 'react';
import { Message } from '../types';

interface ChatMessageProps {
  message: Message;
}

const ChatMessage: React.FC<ChatMessageProps> = ({ message }) => {
  const isUser = message.is_user;
  
  return (
    <div className={`mb-4 flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className={isUser ? 'chat-bubble-user' : 'chat-bubble-bot'}>
        <p className="whitespace-pre-wrap break-words">{message.content}</p>
        {message.timestamp && (
          <p className="text-xs opacity-70 text-right mt-1">
            {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </p>
        )}
      </div>
    </div>
  );
};

export default ChatMessage; 