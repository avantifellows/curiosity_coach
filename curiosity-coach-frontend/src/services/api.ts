import axios from 'axios';
import {
  LoginResponse,
  Message,
  ChatHistory,
  SendMessageResponse,
  ConversationSummary,
  Conversation,
  ConversationCreateResponse,
  ConversationTagsResponse,
  User,
  StudentLoginResponse,
  StudentLoginRequest,
  StudentOptions,
  ProjectSource,
  ProjectSubscriptionResponse,
  SubscribedProject,
  ProjectSection,
  ChapterChatIntentResponse,
  StudentWithConversation,
  PaginatedStudentConversations,
  ConversationWithMessages,
  AnalysisStatus,
  JobStatus,
  UserPersona,
  DashboardResponse,
  StudentDailyMetricsResponse,
  MetricsRefreshResponse,
  Student,
  ConversationLookupResponse,
} from '../types';

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

export const loginUser = async (identifier: string): Promise<LoginResponse> => {
  try {
    const response = await API.post('/auth/login', { identifier: identifier });
    return response.data;
  } catch (error: any) {
    console.error("Login error:", error.response?.data || error.message);
    throw new Error(error.response?.data?.detail || 'Login failed');
  }
};

export const loginStudent = async (studentData: StudentLoginRequest): Promise<StudentLoginResponse> => {
  try {
    const response = await API.post('/auth/student/login', studentData);
    return response.data;
  } catch (error: any) {
    console.error("Student login error:", error.response?.data || error.message);
    throw new Error(error.response?.data?.detail || 'Student login failed');
  }
};

export const getStudentOptions = async (): Promise<StudentOptions> => {
  try {
    const response = await API.get('/config/student-options');
    return response.data;
  } catch (error: any) {
    console.error("Error fetching student options:", error.response?.data || error.message);
    throw new Error(error.response?.data?.detail || 'Failed to get student options');
  }
};

export const getProjectSources = async (options?: {
  availableOnly?: boolean;
}): Promise<ProjectSource[]> => {
  try {
    const params =
      options?.availableOnly === true ? { available_only: true } : undefined;
    const response = await API.get<ProjectSource[]>('/projects/sources', { params });
    return response.data;
  } catch (error: any) {
    console.error("Error fetching project sources:", error.response?.data || error.message);
    const detail = error.response?.data?.detail;
    const msg =
      typeof detail === 'string'
        ? detail
        : detail?.message || 'Failed to fetch project sources';
    throw new Error(msg);
  }
};

export const subscribeToProject = async (kbSourceId: number): Promise<ProjectSubscriptionResponse> => {
  try {
    const response = await API.post<ProjectSubscriptionResponse>('/projects/subscribe', {
      kb_source_id: kbSourceId,
    });
    return response.data;
  } catch (error: any) {
    console.error("Error subscribing to project:", error.response?.data || error.message);
    const detail = error.response?.data?.detail;
    const msg =
      typeof detail === 'string'
        ? detail
        : detail?.message || 'Failed to subscribe to project';
    throw new Error(msg);
  }
};

export const getChapterChatIntent = async (
  kbSourceId: number,
  options?: { sectionId?: number }
): Promise<ChapterChatIntentResponse> => {
  try {
    const params: Record<string, number> = { kb_source_id: kbSourceId };
    if (options?.sectionId != null) {
      params.section_id = options.sectionId;
    }
    const response = await API.get<ChapterChatIntentResponse>(
      '/projects/chapter-chat-intent',
      { params }
    );
    return response.data;
  } catch (error: any) {
    console.error('Error fetching chapter chat intent:', error.response?.data || error.message);
    const d = error.response?.data?.detail;
    throw new Error(
      (typeof d === 'object' && d?.message) || (typeof d === 'string' ? d : null) ||
        'Failed to resolve chapter chat'
    );
  }
};

export const getProjectSections = async (kbSourceId: number): Promise<ProjectSection[]> => {
  try {
    const response = await API.get<ProjectSection[]>(`/projects/${kbSourceId}/sections`);
    return response.data;
  } catch (error: any) {
    console.error('Error fetching project sections:', error.response?.data || error.message);
    const detail = error.response?.data?.detail;
    const msg =
      typeof detail === 'string'
        ? detail
        : detail?.message || 'Failed to fetch project sections';
    throw new Error(msg);
  }
};

export const getSubscribedProjects = async (): Promise<SubscribedProject[]> => {
  try {
    const response = await API.get<SubscribedProject[]>('/projects/subscribed');
    return response.data;
  } catch (error: any) {
    console.error("Error fetching subscribed projects:", error.response?.data || error.message);
    const detail = error.response?.data?.detail;
    const msg =
      typeof detail === 'string'
        ? detail
        : detail?.message || 'Failed to fetch subscribed projects';
    throw new Error(msg);
  }
};

export const refreshClassMetrics = async (
  school: string,
  grade: number,
  section?: string | null,
  includeHourly = true,
  startDate?: string | null,
  endDate?: string | null
): Promise<MetricsRefreshResponse> => {
  try {
    const params: Record<string, string> = {};
    if (startDate) {
      params.start_date = startDate;
    }
    if (endDate) {
      params.end_date = endDate;
    }

    const payload = {
      school,
      grade,
      section: section ?? undefined,
      include_hourly: includeHourly,
    };

    const response = await API.post<MetricsRefreshResponse>('/analytics/refresh', payload, {
      params,
    });
    return response.data;
  } catch (error: any) {
    console.error('Error refreshing class metrics:', error.response?.data || error.message);
    throw new Error(error.response?.data?.detail || 'Failed to refresh metrics');
  }
};

export const getClassDashboardMetrics = async (
  school: string,
  grade: number,
  section?: string | null
): Promise<DashboardResponse> => {
  try {
    const params: Record<string, string | number> = {
      school,
      grade,
    };
    if (section) {
      params.section = section;
    }
    const response = await API.get<DashboardResponse>('/analytics/dashboard', { params });
    return response.data;
  } catch (error: any) {
    console.error('Error fetching dashboard metrics:', error.response?.data || error.message);
    throw new Error(error.response?.data?.detail || 'Failed to fetch dashboard metrics');
  }
};

export const getStudentsForClass = async (
  school: string,
  grade: number,
  section?: string | null,
  tags?: string[],
  tagMode?: 'any' | 'all'
): Promise<StudentWithConversation[]> => {
  try {
    const params: Record<string, string | number> = {
      school,
      grade,
    };
    if (section) {
      params.section = section;
    }
    if (tags && tags.length > 0) {
      params.tags = tags.join(',');
    }
    if (tagMode) {
      params.tag_mode = tagMode;
    }
    const response = await API.get<StudentWithConversation[]>('/students', { params });
    return response.data;
  } catch (error: any) {
    console.error("Error fetching students for class:", error.response?.data || error.message);
    throw new Error(error.response?.data?.detail || 'Failed to fetch students');
  }
};

export const updateStudentTags = async (studentId: number, tags: string[]): Promise<Student> => {
  try {
    const response = await API.patch<Student>(`/students/${studentId}`, { tags });
    return response.data;
  } catch (error: any) {
    console.error(`Error updating tags for student ${studentId}:`, error.response?.data || error.message);
    throw new Error(error.response?.data?.detail || 'Failed to update tags');
  }
};

export const getClassTags = async (
  school: string,
  grade: number,
  section?: string | null,
  query?: string | null
): Promise<string[]> => {
  try {
    const params: Record<string, string | number> = {
      school,
      grade,
    };
    if (section) {
      params.section = section;
    }
    if (query) {
      params.q = query;
    }
    const response = await API.get<string[]>('/students/tags', { params });
    return response.data;
  } catch (error: any) {
    console.error('Error fetching class tags:', error.response?.data || error.message);
    throw new Error(error.response?.data?.detail || 'Failed to fetch tags');
  }
};

export const getConversationTags = async (query?: string | null): Promise<string[]> => {
  try {
    const params: Record<string, string> = {};
    if (query) {
      params.q = query;
    }
    const response = await API.get<string[]>('/conversations/tags', { params });
    return response.data;
  } catch (error: any) {
    console.error('Error fetching conversation tags:', error.response?.data || error.message);
    throw new Error(error.response?.data?.detail || 'Failed to fetch conversation tags');
  }
};

export const getClassConversationTags = async (
  school: string,
  grade: number,
  section?: string | null,
  query?: string | null
): Promise<string[]> => {
  try {
    const params: Record<string, string | number> = {
      school,
      grade,
    };
    if (section) {
      params.section = section;
    }
    if (query) {
      params.q = query;
    }
    const response = await API.get<string[]>('/students/conversation-tags', { params });
    return response.data;
  } catch (error: any) {
    console.error('Error fetching class conversation tags:', error.response?.data || error.message);
    throw new Error(error.response?.data?.detail || 'Failed to fetch conversation tags');
  }
};

export const updateConversationTags = async (
  conversationId: number,
  tags: string[]
): Promise<ConversationTagsResponse> => {
  try {
    const response = await API.patch<ConversationTagsResponse>(`/conversations/${conversationId}/tags`, { tags });
    return response.data;
  } catch (error: any) {
    console.error(`Error updating tags for conversation ${conversationId}:`, error.response?.data || error.message);
    throw new Error(error.response?.data?.detail || 'Failed to update conversation tags');
  }
};

export const updateStudentConversationTags = async (
  studentId: number,
  conversationId: number,
  tags: string[]
): Promise<ConversationTagsResponse> => {
  try {
    const response = await API.patch<ConversationTagsResponse>(
      `/students/${studentId}/conversations/${conversationId}/tags`,
      { tags }
    );
    return response.data;
  } catch (error: any) {
    console.error(
      `Error updating tags for conversation ${conversationId} (student ${studentId}):`,
      error.response?.data || error.message
    );
    throw new Error(error.response?.data?.detail || 'Failed to update conversation tags');
  }
};

export const getStudentDailyMetrics = async (
  school: string,
  grade: number,
  studentIds: number[],
  section?: string | null,
  startDate?: string | null,
  endDate?: string | null
): Promise<StudentDailyMetricsResponse> => {
  if (!studentIds || studentIds.length === 0) {
    throw new Error('At least one student ID is required');
  }

  try {
    const params: Record<string, string | number | (string | number)[]> = {
      school,
      grade,
      student_ids: studentIds,
    };
    if (section) {
      params.section = section;
    }
    if (startDate) {
      params.start_date = startDate;
    }
    if (endDate) {
      params.end_date = endDate;
    }

    const response = await API.get<StudentDailyMetricsResponse>('/analytics/student-daily', {
      params,
      paramsSerializer: (queryParams) => {
        const searchParams = new URLSearchParams();
        Object.entries(queryParams).forEach(([key, value]) => {
          if (value === null || value === undefined) {
            return;
          }
          if (Array.isArray(value)) {
            value.forEach((item) => searchParams.append(key, String(item)));
          } else {
            searchParams.append(key, String(value));
          }
        });
        return searchParams.toString();
      },
    });
    return response.data;
  } catch (error: any) {
    console.error('Error fetching student daily metrics:', error.response?.data || error.message);
    throw new Error(error.response?.data?.detail || 'Failed to fetch student daily metrics');
  }
};

export const getStudentConversations = async (
  studentId: number,
  limit = 3,
  offset = 0,
  day?: string | null,
  tags?: string[],
  tagMode?: 'any' | 'all'
): Promise<PaginatedStudentConversations> => {
  try {
    const params: Record<string, string | number> = {
      limit,
      offset,
    };
    if (day) {
      params.day = day;
    }
    if (tags && tags.length > 0) {
      params.tags = tags.join(',');
    }
    if (tagMode) {
      params.tag_mode = tagMode;
    }
    const response = await API.get<PaginatedStudentConversations>(`/students/${studentId}/conversations`, {
      params,
    });
    return response.data;
  } catch (error: any) {
    console.error(`Error fetching conversations for student ${studentId}:`, error.response?.data || error.message);
    throw new Error(error.response?.data?.detail || 'Failed to fetch conversations');
  }
};

export const getAllStudentConversations = async (
  studentId: number
): Promise<ConversationWithMessages[]> => {
  try {
    const response = await API.get<ConversationWithMessages[]>(`/students/${studentId}/conversations/all`);
    return response.data;
  } catch (error: any) {
    console.error(`Error fetching all conversations for student ${studentId}:`, error.response?.data || error.message);
    throw new Error(error.response?.data?.detail || 'Failed to fetch all conversations');
  }
};

export const getUserPersona = async (userId: number): Promise<UserPersona | null> => {
  try {
    const response = await API.get<UserPersona>(`/internal/users/${userId}/persona`);
    const persona = response.data;
    
    // Parse persona_data if it's a string
    if (persona && typeof persona.persona_data === 'string') {
      persona.persona_data = JSON.parse(persona.persona_data);
    }
    
    return persona;
  } catch (error: any) {
    if (error.response?.status === 404) {
      // No persona found - this is expected for users without personas
      return null;
    }
    console.error(`Error fetching persona for user ${userId}:`, error.response?.data || error.message);
    throw new Error(error.response?.data?.detail || 'Failed to fetch user persona');
  }
};

export interface ClassAnalysisResponse {
  analysis?: string | null;
  status: AnalysisStatus;
  job_id?: string | null;
  computed_at?: string | null;
}

export interface AnalysisJobStatusResponse {
  job_id: string;
  status: JobStatus;
  analysis?: string | null;
  computed_at?: string | null;
  error_message?: string | null;
  analysis_status?: AnalysisStatus | null;
}

export const analyzeClassConversations = async (
  school: string,
  grade: number,
  section?: string | null,
  forceRefresh = false
): Promise<ClassAnalysisResponse> => {
  try {
    const params: Record<string, string | number | boolean> = {
      school,
      grade,
    };
    if (section) {
      params.section = section;
    }
    if (forceRefresh) {
      params.force_refresh = true;
    }
    const response = await API.post<ClassAnalysisResponse>('/students/class-analysis', {}, { params });
    return response.data;
  } catch (error: any) {
    console.error("Error analyzing class conversations:", error.response?.data || error.message);
    throw new Error(error.response?.data?.detail || 'Failed to analyze class conversations');
  }
};

export interface StudentAnalysisResponse {
  analysis?: string | null;
  status: AnalysisStatus;
  job_id?: string | null;
  computed_at?: string | null;
}

export const analyzeStudentConversations = async (
  studentId: number,
  forceRefresh = false
): Promise<StudentAnalysisResponse> => {
  try {
    const params: Record<string, boolean> = {};
    if (forceRefresh) {
      params.force_refresh = true;
    }
    const response = await API.post<StudentAnalysisResponse>(`/students/${studentId}/analysis`, {}, { params });
    return response.data;
  } catch (error: any) {
    console.error("Error analyzing student conversations:", error.response?.data || error.message);
    throw new Error(error.response?.data?.detail || 'Failed to analyze student conversations');
  }
};

export const getAnalysisJobStatus = async (jobId: string): Promise<AnalysisJobStatusResponse> => {
  try {
    const response = await API.get<AnalysisJobStatusResponse>(`/students/analysis-jobs/${jobId}`);
    return response.data;
  } catch (error: any) {
    console.error(`Error fetching analysis job ${jobId} status:`, error.response?.data || error.message);
    throw new Error(error.response?.data?.detail || 'Failed to fetch analysis status');
  }
};

export const sendMessage = async (
  conversationId: number,
  content: string,
  purpose: string = "chat",
  experienceMode?: string
): Promise<SendMessageResponse> => {
  try {
    const response = await API.post<SendMessageResponse>(`/conversations/${conversationId}/messages`, { 
      content,
      purpose,
      experience_mode: experienceMode,
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

export const getConversationLookup = async (conversationId: number): Promise<ConversationLookupResponse> => {
  try {
    const response = await API.get<ConversationLookupResponse>(`/students/conversations/${conversationId}/lookup`);
    return response.data;
  } catch (error: any) {
    console.error("Error fetching conversation lookup:", error.response?.data || error.message);
    throw new Error(error.response?.data?.detail || 'Failed to lookup conversation');
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

export const listConversations = async (
  tags?: string[],
  tagMode?: 'any' | 'all'
): Promise<ConversationSummary[]> => {
  try {
    const params: Record<string, string> = {};
    if (tags && tags.length > 0) {
      params.tags = tags.join(',');
    }
    if (tagMode) {
      params.tag_mode = tagMode;
    }
    const response = await API.get<ConversationSummary[]>('/conversations', { params });
    return response.data;
  } catch (error: any) {
    console.error("Error fetching conversations:", error.response?.data || error.message);
    throw new Error(error.response?.data?.detail || 'Failed to get conversations');
  }
};

export type CreateConversationPayload = {
  title?: string;
  kb_source_id?: number;
  /** DB primary key of rows in `sections` for this kb_source */
  section_id?: number;
  /** Optional per-conversation pipeline override. */
  pipeline_key?: string;
  /** Controls {{QUERY}} placeholder: include, omit, or opening_only. */
  query_mode?: 'include' | 'omit' | 'opening_only';
};

function formatConversationCreateError(detail: unknown): string {
  if (typeof detail === 'string') return detail;
  if (detail && typeof detail === 'object' && 'message' in detail) {
    return String((detail as { message: string }).message);
  }
  return 'Failed to create conversation';
}

export const createConversation = async (
  payload?: string | CreateConversationPayload
): Promise<ConversationCreateResponse> => {
  try {
    const body: Record<string, unknown> =
      typeof payload === 'string'
        ? { title: payload }
        : {
            title: payload?.title ?? 'New Chat',
            ...(payload?.kb_source_id != null
              ? { kb_source_id: payload.kb_source_id }
              : {}),
            ...(payload?.section_id != null ? { section_id: payload.section_id } : {}),
            ...(payload?.pipeline_key ? { pipeline_key: payload.pipeline_key } : {}),
            ...(payload?.query_mode ? { query_mode: payload.query_mode } : {}),
          };
    const response = await API.post<ConversationCreateResponse>('/conversations', body);
    return response.data;
  } catch (error: any) {
    console.error("Error creating conversation:", error.response?.data || error.message);
    const detail = error.response?.data?.detail;
    const err: any = new Error(formatConversationCreateError(detail));
    err.status = error.response?.status;
    if (detail && typeof detail === 'object' && 'code' in detail) {
      err.code = (detail as { code: string }).code;
    }
    throw err;
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

// Create a new prompt
export const createPrompt = async (name: string, description?: string, promptPurpose?: string | null) => {
  try {
    const response = await API.post('/prompts', {
      name,
      description: description || null,
      prompt_purpose: promptPurpose || null
    });
    return response.data;
  } catch (error) {
    console.error("Error creating prompt:", error);
    throw new Error("Failed to create prompt");
  }
};

// Update an existing prompt
export const updatePrompt = async (promptId: number, name?: string, description?: string, promptPurpose?: string | null) => {
  try {
    const payload: any = {};
    if (name !== undefined) payload.name = name;
    if (description !== undefined) payload.description = description;
    if (promptPurpose !== undefined) payload.prompt_purpose = promptPurpose;
    
    const response = await API.put(`/prompts/${promptId}`, payload);
    return response.data;
  } catch (error) {
    console.error(`Error updating prompt ${promptId}:`, error);
    throw new Error(`Failed to update prompt ${promptId}`);
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

// Set a specific version as production
export const setProductionPromptVersion = async (promptId: number | string, versionNumber: number) => {
  try {
    const response = await API.post(`/prompts/${promptId}/versions/${versionNumber}/set-production`);
    return response.data;
  } catch (error) {
    console.error(`Error setting production version ${versionNumber} for prompt ${promptId}:`, error);
    throw new Error(`Failed to set production version for prompt ${promptId}`);
  }
};

// Unset production flag from a version
export const unsetProductionPromptVersion = async (promptId: number | string, versionNumber: number) => {
  try {
    const response = await API.delete(`/prompts/${promptId}/versions/${versionNumber}/unset-production`);
    return response.data;
  } catch (error) {
    console.error(`Error unsetting production version ${versionNumber} for prompt ${promptId}:`, error);
    throw new Error(`Failed to unset production version for prompt ${promptId}`);
  }
};

export const submitFeedback = async (feedbackData: { [key: string]: any }): Promise<any> => {
  try {
    const response = await API.post('/feedback/', {
      feedback_data: feedbackData,
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
