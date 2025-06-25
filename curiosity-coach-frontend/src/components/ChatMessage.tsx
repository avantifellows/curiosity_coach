import React, { useState, useEffect } from 'react';
import { Message } from '../types';

interface ChatMessageProps {
  message: Message;
}

const ChatMessage: React.FC<ChatMessageProps> = ({ message }) => {
  const { content, is_user, status } = message;
  const [ellipsis, setEllipsis] = useState('.');

  useEffect(() => {
    let interval: NodeJS.Timeout | null = null;
    if (status === 'sending') {
      interval = setInterval(() => {
        setEllipsis(prev => {
          if (prev === '...') return '.';
          return prev + '.';
        });
      }, 500); // Adjust speed as needed
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [status]);

  const alignment = is_user ? 'justify-end' : 'justify-start';
  const bgGradient = is_user 
    ? 'bg-gradient-to-r from-indigo-500 to-purple-600' 
    : 'bg-gradient-to-r from-gray-100 to-blue-100';
  const textColor = is_user ? 'text-white' : 'text-gray-700';
  const opacity = status === 'sending' ? 'opacity-70' : 'opacity-100';
  const errorStyle = status === 'error' ? 'border border-red-500' : '';
  const hoverEffect = 'transition-all duration-200 hover:shadow-lg';

  return (
    <div className={`flex ${alignment} ${opacity} px-1 sm:px-0`}>
      <div className={`rounded-lg px-3 sm:px-4 py-2 max-w-[85%] sm:max-w-xs lg:max-w-md shadow ${bgGradient} ${textColor} ${errorStyle} ${hoverEffect} whitespace-pre-wrap break-words`}>
        {content}
        {status === 'sending' && (
          <span className="text-xs italic ml-2 block opacity-80">
            sending{ellipsis}
          </span>
        )}
        {status === 'error' && (
            <span className="text-xs italic ml-2 block text-red-300">
                Failed to send
            </span>
        )}
      </div>
    </div>
  );
};

export default ChatMessage; 