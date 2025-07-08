import axios from 'axios';
import { LoginResponse, Message, ChatHistory, SendMessageResponse, ConversationSummary, Conversation, User } from '../types';

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
    console.error("Login error:", error.response?.data || error.message);
    throw new Error(error.response?.data?.detail || 'Login failed');
  }
};

export const sendMessage = async (conversationId: number, content: string, purpose: string = "chat"): Promise<SendMessageResponse> => {
  try {
    const response = await API.post<SendMessageResponse>(`/conversations/${conversationId}/messages`, { 
      content,
      purpose 
    });
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

export const updateConversationTitleApi = async (conversationId: number, newTitle: string): Promise<Conversation> => {
  try {
    const response = await API.put<Conversation>(`/conversations/${conversationId}/title`, { title: newTitle });
    return response.data;
  } catch (error: any) {
    console.error(`Error updating conversation title for ID ${conversationId}:`, error.response?.data || error.message);
    throw new Error(error.response?.data?.detail || 'Failed to update conversation title');
  }
};

// New function to get pipeline steps for an AI message
export const getPipelineSteps = async (aiMessageId: number | string): Promise<any[]> => {
  try {
    // The interceptor automatically adds the Authorization header
    const response = await API.get<any[]>(`/messages/${aiMessageId}/pipeline_steps`);
    return response.data;
  } catch (error: any) {
    console.error(`Error fetching pipeline steps for AI message ID ${aiMessageId}:`, error.response?.data || error.message);
    // If the error is a 404, or if no specific steps are found, the backend returns [] which is fine.
    // For other errors, we might want to throw or return a specific error object.
    // For now, let's re-throw to be handled by the caller, similar to other functions.
    throw new Error(error.response?.data?.detail || `Failed to fetch pipeline steps for message ${aiMessageId}`);
  }
};

// --- Prompt Versioning API Methods ---

// Get a list of all prompts
export const getPrompts = async () => {
  try {
    const response = await API.get('/prompts');
    return response.data;
  } catch (error) {
    console.error("Error fetching prompts:", error);
    throw new Error("Failed to fetch prompts");
  }
};

// Get a specific prompt by name or ID
export const getPrompt = async (nameOrId: string | number) => {
  try {
    const response = await API.get(`/prompts/${nameOrId}`);
    return response.data;
  } catch (error) {
    console.error(`Error fetching prompt ${nameOrId}:`, error);
    throw new Error(`Failed to fetch prompt ${nameOrId}`);
  }
};

// Get all versions of a specific prompt
export const getPromptVersions = async (nameOrId: string | number) => {
  try {
    const response = await API.get(`/prompts/${nameOrId}/versions`);
    return response.data;
  } catch (error) {
    console.error(`Error fetching versions for prompt ${nameOrId}:`, error);
    throw new Error(`Failed to fetch versions for prompt ${nameOrId}`);
  }
};

// Get the active version of a specific prompt
export const getActivePromptVersion = async (nameOrId: string | number) => {
  try {
    const response = await API.get(`/prompts/${nameOrId}/versions/active`);
    return response.data;
  } catch (error) {
    console.error(`Error fetching active version for prompt ${nameOrId}:`, error);
    throw new Error(`Failed to fetch active version for prompt ${nameOrId}`);
  }
};

// Create a new version of a prompt
export const createPromptVersion = async (promptId: number | string, promptText: string) => {
  try {
    const response = await API.post(`/prompts/${promptId}/versions`, {
      prompt_text: promptText
    });
    return response.data;
  } catch (error) {
    console.error(`Error creating new version for prompt ${promptId}:`, error);
    throw new Error(`Failed to create new version for prompt ${promptId}`);
  }
};

// Set a specific version as active
export const setActivePromptVersion = async (promptId: number | string, versionId: number) => {
  try {
    const response = await API.post(`/prompts/${promptId}/versions/set-active/`, {
      version_id: versionId
    });
    return response.data;
  } catch (error) {
    console.error(`Error setting active version ${versionId} for prompt ${promptId}:`, error);
    throw new Error(`Failed to set active version for prompt ${promptId}`);
  }
};

export const submitFeedback = async (thumbsUp: boolean, feedbackText?: string): Promise<any> => {
  try {
    const response = await API.post('/feedback/', {
      thumbs_up: thumbsUp,
      feedback_text: feedbackText,
    });
    return response.data;
  } catch (error: any) {
    console.error("Error submitting feedback:", error.response?.data || error.message);
    throw new Error(error.response?.data?.detail || 'Failed to submit feedback');
  }
};

export const getConversationMemory = async (conversationId: number | string): Promise<any> => {
  try {
    const response = await API.get(`/conversations/${conversationId}/memory`);
    return response.data;
  } catch (error: any) {
    console.error(`Error fetching memory for conversation ID ${conversationId}:`, error.response?.data || error.message);
    if (axios.isAxiosError(error) && error.response?.status === 404) {
      return null;
    }
    throw new Error(error.response?.data?.detail || `Failed to fetch memory for conversation ${conversationId}`);
  }
}; 