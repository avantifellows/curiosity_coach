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
  tags?: string[];
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

export interface DashboardClassSummary {
  cohort_start: string;
  cohort_end: string;
  total_students: number | null;
  total_conversations: number | null;
  total_user_messages: number | null;
  total_ai_messages: number | null;
  total_user_words: number | null;
  total_ai_words: number | null;
  total_minutes: number | null;
  avg_minutes_per_conversation: number | null;
  avg_user_msgs_per_conversation: number | null;
  avg_ai_msgs_per_conversation: number | null;
  avg_user_words_per_conversation: number | null;
  avg_ai_words_per_conversation: number | null;
  avg_user_words_per_message: number | null;
  avg_ai_words_per_message: number | null;
  user_messages_after_school: number | null;
  total_messages_after_school: number | null;
  after_school_conversations: number | null;
  after_school_user_pct: number | null;
  total_relevant_questions: number | null;
  avg_attention_span?: number | null;
  depth_levels?: DepthLevelStat[] | null;
  top_topics?: ConversationTopic[] | null;
}

export interface DashboardDailyStat {
  day: string;
  total_minutes: number | null;
  total_user_messages: number | null;
  total_ai_messages: number | null;
  active_students: number | null;
  user_messages_after_school: number | null;
  after_school_conversations: number | null;
  total_relevant_questions: number | null;
  avg_attention_span?: number | null;
  depth_levels?: DepthLevelStat[] | null;
  top_topics?: ConversationTopic[] | null;
}

export interface DashboardStudentSnapshot {
  student_id: number;
  student_name?: string | null;
  total_minutes: number | null;
  total_user_messages: number | null;
  total_user_words: number | null;
  total_ai_messages: number | null;
  after_school_user_pct: number | null;
  avg_words_per_message: number | null;
  total_relevant_questions: number | null;
  avg_attention_span?: number | null;
  depth_levels?: DepthLevelStat[] | null;
  top_topics?: ConversationTopic[] | null;
}

export interface DashboardHourlyBucket {
  window_start: string;
  window_end: string;
  user_message_count: number;
  ai_message_count: number;
  active_users: number;
  after_school_user_count: number;
}

export interface DashboardResponse {
  class_summary: DashboardClassSummary | null;
  recent_days: DashboardDailyStat[];
  student_snapshots: DashboardStudentSnapshot[];
  hourly_activity: DashboardHourlyBucket[];
}

export interface StudentDailyRecord {
  day: string;
  user_messages: number | null;
  ai_messages: number | null;
  user_words: number | null;
  ai_words: number | null;
  minutes_spent: number | null;
  user_messages_after_school: number | null;
  total_messages_after_school: number | null;
  total_relevant_questions?: number | null;
  avg_attention_span?: number | null;
  depth_levels?: DepthLevelStat[] | null;
  max_depth?: number | null;
  max_depth_conversation_id?: number | null;
}

export interface StudentDailySeries {
  student_id: number;
  student_name?: string | null;
  records: StudentDailyRecord[];
}

export interface StudentDailyMetricsResponse {
  students: StudentDailySeries[];
}

export interface MetricsRefreshResponse {
  class_daily_rows: number;
  student_daily_rows: number;
  class_summary_rows: number;
  student_summary_rows: number;
  hourly_rows: number;
  deleted_rows: Record<string, number>;
}

export interface ConversationMessage {
  id: number;
  content: string;
  is_user: boolean;
  timestamp: string;
  curiosity_score?: number;
}

export interface ConversationTopic {
  term: string;
  weight?: number | null;
  count?: number | null;
  total_weight?: number | null;
  conversation_count?: number | null;
}

export interface DepthLevelStat {
  level: number;
  count: number;
}

export interface ConversationEvaluationMetrics {
  depth?: number | null;
  relevant_question_count?: number | null;
  topics: ConversationTopic[];
  attention_span?: number | null;
  avg_attention_span?: number | null;
  attention_sample_size?: number | null;
  total_attention_span?: number | null;
  computed_at?: string | null;
  status?: string | null;
  prompt_version_id?: number | null;
  depth_sample_size?: number | null;
  relevant_sample_size?: number | null;
  conversation_count?: number | null;
}

export interface ConversationCuriositySummary {
  average?: number | null;
  latest?: number | null;
  sample_size: number;
}

export interface ConversationWithMessages {
  id: number;
  title: string | null;
  created_at: string;
  updated_at: string;
  messages: ConversationMessage[];
  evaluation?: ConversationEvaluationMetrics | null;
  curiosity_summary?: ConversationCuriositySummary | null;
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

// Flexible persona structure to allow prompt experimentation
// Accept any key-value structure from the backend
export interface UserPersonaData {
  [key: string]: string | number | boolean | object;
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
