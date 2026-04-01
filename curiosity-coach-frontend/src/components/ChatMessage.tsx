import React, { useState, useEffect, useMemo } from 'react';
import { Message } from '../types';
import { AutoAwesomeRounded } from '@mui/icons-material';
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
  
  const surfaceClasses = is_user
    ? 'bg-violet-600 text-white'
    : 'border border-violet-200 bg-[#faf7ff] text-slate-800';

  const opacity = status === 'sending' ? 'opacity-70' : 'opacity-100';
  const errorStyle = status === 'error' ? 'border border-red-500' : '';
  
  // Keep entrance motion subtle; chat should feel stable, not flashy.
  const hoverEffect = 'transition-all duration-200';
  const appearAnimation = isVisible 
    ? (is_user ? 'translate-y-0 opacity-100' : 'translate-y-0 opacity-100') 
    : (is_user ? 'translate-y-2 opacity-0' : 'translate-y-2 opacity-0');
  const animationTiming = is_user ? 'transition-all duration-300 ease-out' : 'transition-all duration-300 ease-out delay-100';

  return (
    <div className={`flex ${alignment} ${opacity} px-4 sm:px-6 lg:px-8 ${animationTiming} ${appearAnimation}`}>
      {/* AI Avatar for non-user messages */}
      {!is_user && (
        <div className="mr-2 flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-violet-100">
          <AutoAwesomeRounded fontSize="small" className="text-violet-700" />
        </div>
      )}
      
      <div className={`min-w-[120px] max-w-[75%] whitespace-pre-wrap break-words rounded-2xl px-3 py-2 shadow-sm sm:max-w-md sm:px-4 ${surfaceClasses} ${errorStyle} ${hoverEffect} lg:max-w-lg`}>
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
