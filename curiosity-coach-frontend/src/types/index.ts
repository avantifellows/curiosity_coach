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

// Add type for the sendMessage API response
export interface SendMessageResponse {
  success: boolean;
  message: Message; // The actual message object created by the backend
}

export interface ApiError {
  message: string;
  status?: number;
} 