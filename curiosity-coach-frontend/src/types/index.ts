export interface User {
  id: number;
  phone_number?: string;
  username?: string;
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
  generated_username?: string;
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

// Add the following prompt-related types to the types file

// Prompt version
export interface PromptVersion {
  id: number;
  prompt_id: number;
  version_number: number;
  prompt_text: string;
  is_active: boolean;
  created_at: string;
}

// Prompt with versions
export interface Prompt {
  id: number;
  name: string;
  description: string;
  created_at: string;
  updated_at: string;
  versions: PromptVersion[];
  active_prompt_version: PromptVersion | null;
}

// Simple prompt representation
export interface PromptSimple {
  id: number;
  name: string;
  description: string;
  created_at: string;
  updated_at: string;
  active_version_number: number | null;
  active_version_text: string | null;
} 