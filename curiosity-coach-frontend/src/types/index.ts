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
}

export interface ChatHistory {
  messages: Message[];
}

export interface LoginResponse {
  success: boolean;
  message: string;
  user?: User;
}

export interface ApiError {
  message: string;
  status?: number;
} 