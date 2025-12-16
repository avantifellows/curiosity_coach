export interface User {
  id: number;
  phone_number?: string;
  name?: string;
  student?: Student;  // Include student profile if user is a student
}

export interface Message {
  id?: number;
  content: string;
  is_user: boolean;
  timestamp?: string;
  user_id?: number;
  status?: 'sending' | 'sent' | 'error';
  curiosity_score?: number;
}

export interface ChatHistory {
  messages: Message[];
}

export interface LoginResponse {
  success: boolean;
  message: string;
  user?: User;
  generated_name?: string;
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

export type AnalysisStatus = 'ready' | 'queued' | 'running' | 'failed';
export type JobStatus = 'queued' | 'running' | 'completed' | 'failed';

// --- Conversation Types ---

/**
 * Represents the summary of a conversation, typically used for lists.
 */
export interface ConversationSummary {
  id: number;
  title: string | null; // Title can be optional or default
  updated_at: string; // ISO date string
  visit_number?: number; // Visit number at creation time (1, 2, 3, 4+)
}

/**
 * Represents a full conversation object, including user ID.
 */
export interface Conversation extends ConversationSummary {
  user_id: number;
  created_at: string; // ISO date string
  visit_number?: number; // Visit number at creation time
  prompt_version_id?: number; // ID of the prompt version used
}

/**
 * Response from creating a new conversation (with onboarding data)
 */
export interface ConversationCreateResponse {
  conversation: Conversation;
  visit_number: number;
  ai_opening_message?: string;
  preparation_status: 'ready' | 'generating_memory' | 'generating_persona';
  requires_opening_message: boolean;
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
  is_production: boolean;
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
  prompt_purpose: string | null;
  created_at: string;
  updated_at: string;
  active_version_number: number | null;
  active_version_text: string | null;
}

// --- Student Types ---

export interface Student {
  id: number;
  user_id: number;
  school: string;
  grade: number;
  section?: string | null;
  roll_number: number;
  first_name: string;
  created_at: string;
}

export interface StudentLoginRequest {
  school: string;
  grade: number;
  section?: string | null;
  roll_number: number;
  first_name: string;
}

export interface StudentLoginResponse {
  success: boolean;
  message: string;
  user?: User;
  student?: Student;
}

export interface StudentOptions {
  schools: string[];
  grades: number[];
  sections: string[];
}

export interface ConversationMessage {
  id: number;
  content: string;
  is_user: boolean;
  timestamp: string;
  curiosity_score?: number;
}

export interface ConversationWithMessages {
  id: number;
  title: string | null;
  updated_at: string;
  messages: ConversationMessage[];
}

export interface StudentWithConversation {
  student: Student;
  latest_conversation?: ConversationWithMessages | null;
}

export interface PaginatedStudentConversations {
  conversations: ConversationWithMessages[];
  next_offset: number | null;
}

// --- User Persona Types ---

export interface UserPersonaData {
  what_works: string;
  what_doesnt_work: string;
  interests: string;
  learning_style: string;
  engagement_triggers: string;
  red_flags: string;
}

export interface UserPersona {
  id: number;
  user_id: number;
  persona_data: UserPersonaData | string; // Can be parsed object or JSON string from backend
  created_at: string;
  updated_at: string;
}

// --- End User Persona Types ---

// --- End Student Types --- 
