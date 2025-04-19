import React from 'react';
import { Box, Paper, Typography } from '@mui/material';
import { Message } from '../types';

interface ChatMessageProps {
  message: Message;
}

const ChatMessage: React.FC<ChatMessageProps> = ({ message }) => {
  const isUser = message.is_user;
  
  return (
    <Box
      sx={{
        display: 'flex',
        justifyContent: isUser ? 'flex-end' : 'flex-start',
        mb: 2,
      }}
    >
      <Paper
        elevation={1}
        sx={{
          p: 2,
          maxWidth: '75%',
          backgroundColor: isUser ? '#e3f2fd' : '#f5f5f5',
          borderRadius: 2,
        }}
      >
        <Typography variant="body1">{message.content}</Typography>
        {message.timestamp && (
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1, textAlign: 'right' }}>
            {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </Typography>
        )}
      </Paper>
    </Box>
  );
};

export default ChatMessage; 