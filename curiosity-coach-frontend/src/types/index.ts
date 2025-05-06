export interface User {
  id: number;
  phone_number: string;
}

export interface Message {
  id?: number;
  content: string;
  is_user: boolean;
  timestamp?: string;
  user_id?: number;
  status?: 'sending' | 'sent' | 'error';
}

export interface ChatHistory {
  messages: Message[];
}

export interface LoginResponse {
  success: boolean;
  message: string;
  user?: User;
}

// Add type for the sendMessage API response
export interface SendMessageResponse {
  success: boolean;
  message: Message; // The actual message object created by the backend
}

export interface ApiError {
  message: string;
  status?: number;
}

// --- Conversation Types ---

/**
 * Represents the summary of a conversation, typically used for lists.
 */
export interface ConversationSummary {
  id: number;
  title: string | null; // Title can be optional or default
  updated_at: string; // ISO date string
}

/**
 * Represents a full conversation object, including user ID.
 */
export interface Conversation extends ConversationSummary {
  user_id: number;
  created_at: string; // ISO date string
}

// --- End Conversation Types --- 