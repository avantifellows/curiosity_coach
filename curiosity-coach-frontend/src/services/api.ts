import axios from 'axios';
import { LoginResponse, Message, ChatHistory, SendMessageResponse } from '../types';

const API = axios.create({
  baseURL: process.env.REACT_APP_BACKEND_BASE_URL + '/api' || '/api',
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

// Fetches the specific AI response corresponding to a given user message ID
// Note: This requires a corresponding backend endpoint, e.g., GET /api/messages/{user_message_id}/response
export const getAiResponseForUserMessage = async (userMessageId: string | number): Promise<{ message: Message } | null> => {
  try {
    // Construct the endpoint URL using the user message ID
    // Changed the expected type here slightly, as the raw response might be the message directly
    const response = await API.get<Message | { message: Message } | null>(`/messages/${userMessageId}/response`);
    
    // Check if the response data itself is the message object
    if (response.data && 'id' in response.data && 'content' in response.data && 'is_user' in response.data && 'timestamp' in response.data && !('message' in response.data)) {
      // If response.data is the message, wrap it in the expected structure
      return { message: response.data };
    } 
    // Check if the response data contains the message nested under a 'message' key (original logic)
    else if (response.data && 'message' in response.data && response.data.message) {
        // Return the nested message directly
        return { message: response.data.message };
    } 
    // Otherwise, the message is not ready or the response is empty/invalid
    else {
        return null; 
    }
  } catch (error: any) {
    // Log the error but return null to allow polling to continue
    // Avoid throwing an error here, as that would stop the polling loop prematurely
    console.error(`[API] Error fetching AI response for user message ${userMessageId}:`, error.response?.data || error.message);
    // Optionally: Check for specific error codes (e.g., 404) to differentiate between 'not found yet' and actual server errors.
    // For now, treat any error as 'response not ready'
    return null; 
  }
}; 