import React, { useState, useEffect, useMemo } from 'react';
import { Message } from '../types';
import { SmartToy } from '@mui/icons-material';
import parse from 'html-react-parser';

const escapeHtml = (raw: string): string =>
  raw
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');

const formatMessageContent = (content: string): React.ReactNode => {
  const safe = escapeHtml(content);
  const withLineBreaks = safe.replace(/\n/g, '<br />');
  const withBold = withLineBreaks.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  return parse(withBold);
};

interface ChatMessageProps {
  message: Message;
}

const ChatMessage: React.FC<ChatMessageProps> = ({ message }) => {
  const { content, is_user, status } = message;
  const [ellipsis, setEllipsis] = useState('.');
  const [isVisible, setIsVisible] = useState(false);
  const formattedContent = useMemo(() => formatMessageContent(content), [content]);

  useEffect(() => {
    // Animation effect when message appears
    setIsVisible(true);
    
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

  // Improved alignment with spacing from edges
  const alignment = is_user ? 'justify-end' : 'justify-start';
  
  // Gradient backgrounds
  const bgGradient = is_user 
    ? 'bg-gradient-to-r from-indigo-500 to-purple-600' 
    : 'bg-gradient-to-r from-gray-100 to-blue-100';
  
  const textColor = is_user ? 'text-white' : 'text-gray-700';
  const opacity = status === 'sending' ? 'opacity-70' : 'opacity-100';
  const errorStyle = status === 'error' ? 'border border-red-500' : '';
  
  // Enhanced hover and animation effects
  const hoverEffect = 'transition-all duration-200 hover:shadow-lg';
  const appearAnimation = isVisible 
    ? (is_user ? 'translate-y-0 opacity-100' : 'translate-y-0 opacity-100') 
    : (is_user ? 'translate-y-2 opacity-0' : 'translate-y-2 opacity-0');
  const animationTiming = is_user ? 'transition-all duration-300 ease-out' : 'transition-all duration-300 ease-out delay-100';

  return (
    <div className={`flex ${alignment} ${opacity} px-4 sm:px-6 lg:px-8 ${animationTiming} ${appearAnimation}`}>
      {/* AI Avatar for non-user messages */}
      {!is_user && (
        <div className="flex-shrink-0 h-8 w-8 rounded-full bg-indigo-100 flex items-center justify-center mr-2">
          <SmartToy fontSize="small" className="text-indigo-600" />
        </div>
      )}
      
      <div className={`rounded-xl px-3 sm:px-4 py-2 max-w-[75%] sm:max-w-md lg:max-w-lg shadow ${bgGradient} ${textColor} ${errorStyle} ${hoverEffect} whitespace-pre-wrap break-words min-w-[120px]`}>
        {formattedContent}
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
      
      {/* User Avatar - optional, uncomment if you want user avatars too */}
      {/* {is_user && (
        <div className="flex-shrink-0 h-8 w-8 rounded-full bg-indigo-500 flex items-center justify-center ml-2">
          <span className="text-white text-sm font-bold">You</span>
        </div>
      )} */}
    </div>
  );
};

export default ChatMessage; 
