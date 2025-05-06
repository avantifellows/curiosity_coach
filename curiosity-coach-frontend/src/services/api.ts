import axios from 'axios';
import { LoginResponse, Message, ChatHistory, SendMessageResponse, ConversationSummary, Conversation, User } from '../types';

const API = axios.create({
  baseURL: process.env.REACT_APP_BACKEND_BASE_URL || '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add authorization token to requests if user is logged in
API.interceptors.request.use((config) => {
  const userJson = localStorage.getItem('user');
  if (userJson) {
    const user = JSON.parse(userJson);
    config.headers.Authorization = `Bearer ${user.id}`;
  }
  return config;
});

export const loginUser = async (phoneNumber: string): Promise<LoginResponse> => {
  try {
    const response = await API.post('/auth/login', { phone_number: phoneNumber });
    return response.data;
  } catch (error: any) {
    console.error("Login error:", error.response?.data || error.message);
    throw new Error(error.response?.data?.detail || 'Login failed');
  }
};

export const sendMessage = async (conversationId: number, content: string): Promise<SendMessageResponse> => {
  try {
    const response = await API.post<SendMessageResponse>(`/conversations/${conversationId}/messages`, { content });
    return response.data;
  } catch (error: any) {
    console.error("Error sending message:", error.response?.data || error.message);
    throw new Error(error.response?.data?.detail || 'Failed to send message');
  }
};

export const getConversationMessages = async (conversationId: number): Promise<ChatHistory> => {
  try {
    const response = await API.get<ChatHistory>(`/conversations/${conversationId}/messages`);
    return response.data;
  } catch (error: any) {
    console.error("Error fetching messages:", error.response?.data || error.message);
    throw new Error(error.response?.data?.detail || 'Failed to get messages');
  }
};

export const getAiResponseForUserMessage = async (userMessageId: number): Promise<Message | null> => {
  try {
    const response = await API.get<Message | null>(`/messages/${userMessageId}/response`);
    return response.data;
  } catch (error: any) {
    console.error(`[API] Error fetching AI response for user message ${userMessageId}:`, error.response?.data || error.message);
    if (axios.isAxiosError(error) && error.response?.status === 404) {
      console.log(`[API] Response for message ${userMessageId} not found (404).`);
      return null;
    }
    return null;
  }
};

export const listConversations = async (): Promise<ConversationSummary[]> => {
  try {
    const response = await API.get<ConversationSummary[]>('/conversations');
    return response.data;
  } catch (error: any) {
    console.error("Error fetching conversations:", error.response?.data || error.message);
    throw new Error(error.response?.data?.detail || 'Failed to get conversations');
  }
};

export const createConversation = async (title?: string): Promise<Conversation> => {
  try {
    const payload = title ? { title } : {};
    const response = await API.post<Conversation>('/conversations', payload);
    return response.data;
  } catch (error: any) {
    console.error("Error creating conversation:", error.response?.data || error.message);
    throw new Error(error.response?.data?.detail || 'Failed to create conversation');
  }
};

// Add a function to verify auth status by calling /auth/me
export const verifyAuthStatus = async (): Promise<User> => {
  try {
    // The interceptor automatically adds the Authorization header
    const response = await API.get<User>('/auth/me'); 
    return response.data;
  } catch (error: any) {
    console.error("Auth status verification failed:", error.response?.data || error.message);
    // Re-throw the error so the caller (AuthProvider) knows verification failed
    throw new Error(error.response?.data?.detail || 'Session verification failed');
  }
}; 