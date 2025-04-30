import axios from 'axios';
import { LoginResponse, Message, ChatHistory, SendMessageResponse } from '../types';

const API = axios.create({
  baseURL: '/api',
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
    throw new Error(error.response?.data?.message || 'Login failed');
  }
};

export const sendMessage = async (content: string): Promise<SendMessageResponse> => {
  try {
    const response = await API.post<SendMessageResponse>('/messages', { content });
    return response.data;
  } catch (error: any) {
    throw new Error(error.response?.data?.message || 'Failed to send message');
  }
};

export const getChatHistory = async (): Promise<ChatHistory> => {
  try {
    const response = await API.get('/messages/history');
    return response.data;
  } catch (error: any) {
    throw new Error(error.response?.data?.message || 'Failed to get chat history');
  }
}; 