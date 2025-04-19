import React, { useState, useEffect, useRef } from 'react';
import { Box, TextField, Button, Paper, Typography, Container, CircularProgress, IconButton, Tooltip } from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import LogoutIcon from '@mui/icons-material/Logout';
import ChatMessage from './ChatMessage';
import { useAuth } from '../context/AuthContext';
import { sendMessage, getChatHistory } from '../services/api';
import { Message } from '../types';
import { useNavigate } from 'react-router-dom';

const ChatInterface: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [newMessage, setNewMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { user, isLoading: authLoading, logout } = useAuth();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  // Fetch chat history when component mounts
  useEffect(() => {
    const fetchChatHistory = async () => {
      if (!user) return; // Don't fetch if user is not available
      
      try {
        setLoading(true);
        const response = await getChatHistory();
        setMessages(response.messages || []);
      } catch (err: any) {
        setError('Failed to load chat history. Please try again later.');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    if (user && !authLoading) {
      fetchChatHistory();
    }
  }, [user, authLoading]);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!newMessage.trim() || !user) return;
    
    // Optimistically add message to UI
    const userMessage: Message = {
      content: newMessage.trim(),
      is_user: true,
      timestamp: new Date().toISOString(),
    };
    
    setMessages((prev) => [...prev, userMessage]);
    setNewMessage('');
    setError(null);
    
    try {
      // Send message to backend
      await sendMessage(userMessage.content);
      
      // In a real app, you would wait for the response message from the backend
      // For now, we'll simulate a response after a short delay
      setLoading(true);
      
      // This is placeholder - in reality, you would listen for the response from your message queue
      setTimeout(async () => {
        try {
          // Refetch chat history to get the response
          const history = await getChatHistory();
          setMessages(history.messages || []);
        } catch (err) {
          setError('Failed to receive response. Please try again.');
          console.error(err);
        } finally {
          setLoading(false);
        }
      }, 1000);
      
    } catch (err: any) {
      setError('Failed to send message. Please try again.');
      console.error(err);
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  if (authLoading) {
    return (
      <Container maxWidth="md">
        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
          <CircularProgress />
          <Typography variant="body1" sx={{ ml: 2 }}>
            Loading chat...
          </Typography>
        </Box>
      </Container>
    );
  }

  return (
    <Container maxWidth="md">
      <Box sx={{ display: 'flex', flexDirection: 'column', height: '80vh', mt: 3 }}>
        <Paper elevation={3} sx={{ p: 2, mb: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Box>
            <Typography variant="h5" component="h1">
              Chat with Curiosity Coach
            </Typography>
            <Typography variant="subtitle1" color="text.secondary">
              {user ? `Logged in as: ${user.phone_number}` : 'Please log in'}
            </Typography>
          </Box>
          <Tooltip title="Logout">
            <IconButton 
              color="primary" 
              onClick={handleLogout}
              aria-label="logout"
            >
              <LogoutIcon />
            </IconButton>
          </Tooltip>
        </Paper>

        {/* Chat messages */}
        <Paper 
          elevation={2} 
          sx={{ 
            p: 2, 
            mb: 2, 
            flexGrow: 1, 
            overflow: 'auto',
            display: 'flex',
            flexDirection: 'column'
          }}
        >
          {loading && messages.length === 0 ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
              <CircularProgress />
            </Box>
          ) : messages.length === 0 ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
              <Typography variant="body1" color="text.secondary">
                No messages yet. Start a conversation!
              </Typography>
            </Box>
          ) : (
            messages.map((message, index) => (
              <ChatMessage key={index} message={message} />
            ))
          )}
          <div ref={messagesEndRef} />
        </Paper>

        {/* Message input */}
        <Paper elevation={2} sx={{ p: 2 }}>
          {error && (
            <Typography color="error" variant="body2" sx={{ mb: 2 }}>
              {error}
            </Typography>
          )}
          
          <Box component="form" onSubmit={handleSendMessage} sx={{ display: 'flex' }}>
            <TextField
              fullWidth
              placeholder="Type your message..."
              variant="outlined"
              value={newMessage}
              onChange={(e) => setNewMessage(e.target.value)}
              disabled={!user || loading}
              sx={{ mr: 1 }}
            />
            <Button
              type="submit"
              variant="contained"
              color="primary"
              endIcon={loading ? <CircularProgress size={20} color="inherit" /> : <SendIcon />}
              disabled={!user || loading || !newMessage.trim()}
            >
              Send
            </Button>
          </Box>
        </Paper>
      </Box>
    </Container>
  );
};

export default ChatInterface; 