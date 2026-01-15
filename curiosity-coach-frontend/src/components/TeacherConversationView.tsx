import React, { useCallback, useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { ConversationWithMessages, Student, UserPersona, UserPersonaData } from '../types';
import { getStudentConversations, getUserPersona } from '../services/api';

interface ConversationLocationState {
  student?: Student;
  school?: string;
  grade?: number;
  section?: string | null;
}

const PAGE_SIZE = 3;

// Helper to ensure persona_data is parsed
const getPersonaData = (persona: UserPersona | null): UserPersonaData | null => {
  if (!persona) return null;
  if (typeof persona.persona_data === 'string') {
    try {
      return JSON.parse(persona.persona_data);
    } catch {
      return null;
    }
  }
  return persona.persona_data;
};

// Helper to format snake_case keys to Title Case for display
const formatPersonaKey = (key: string): string => {
  // Skip internal metadata keys (starting with _)
  if (key.startsWith('_')) return '';
  
  return key
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
};

// Helper to get emoji for persona field (basic mapping)
const getPersonaEmoji = (key: string): string => {
  const lowerKey = key.toLowerCase();
  if (lowerKey.includes('work') && !lowerKey.includes('doesnt')) return '✅';
  if (lowerKey.includes('doesnt') || lowerKey.includes('red') || lowerKey.includes('flag')) return '❌';
  if (lowerKey.includes('interest') || lowerKey.includes('topic')) return '💡';
  if (lowerKey.includes('learning') || lowerKey.includes('style') || lowerKey.includes('profile')) return '📚';
  if (lowerKey.includes('trigger') || lowerKey.includes('engagement')) return '⚡';
  return '📝'; // default emoji
};

const formatInteger = (value: number | null | undefined) =>
  value === null || value === undefined ? '—' : new Intl.NumberFormat().format(value);

const formatOneDecimal = (value: number | null | undefined) =>
  value === null || value === undefined
    ? '—'
    : new Intl.NumberFormat(undefined, {
        minimumFractionDigits: 1,
        maximumFractionDigits: 1,
      }).format(value);

// Get the latest non-null curiosity score from messages
const getLatestCuriosityScore = (messages: ConversationWithMessages['messages']): number | null => {
  // Messages are ordered by timestamp, find last one with a score
  for (let i = messages.length - 1; i >= 0; i--) {
    if (!messages[i].is_user && typeof messages[i].curiosity_score === 'number') {
      return messages[i].curiosity_score!;
    }
  }
  return null;
};

// Check if a conversation happened during after-school hours
const isAfterSchoolHours = (createdAt: string): boolean => {
  const date = new Date(createdAt);
  const dayOfWeek = date.getUTCDay(); // 0 = Sunday, 6 = Saturday
  const hours = date.getUTCHours();
  
  // Weekends (Saturday = 6, Sunday = 0): all day is considered "after school"
  if (dayOfWeek === 0 || dayOfWeek === 6) {
    return true;
  }
  
  // Weekdays: after 12:00 UTC or before 3:00 UTC
  // This represents evening/night hours (roughly 5:30 PM IST to 8:30 AM IST next day)
  return hours >= 12 || hours < 3;
};

const TeacherConversationView: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const state = (location.state as ConversationLocationState) || {};
  const student = state.student;
  const classInfo = {
    school: state.school ?? student?.school,
    grade: state.grade ?? student?.grade,
    section: state.section ?? student?.section ?? undefined,
  };
  const [conversations, setConversations] = useState<ConversationWithMessages[]>([]);
  const [nextOffset, setNextOffset] = useState<number | null>(null);
  const [isInitialLoading, setIsInitialLoading] = useState(false);
  const [isLoadMore, setIsLoadMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [persona, setPersona] = useState<UserPersona | null>(null);
  const [personaLoading, setPersonaLoading] = useState(false);
  const [showAfterSchoolOnly, setShowAfterSchoolOnly] = useState(false);

  const fetchConversations = useCallback(
    async (offset = 0) => {
      if (!student) {
        return;
      }
      if (offset === 0) {
        setIsInitialLoading(true);
      } else {
        setIsLoadMore(true);
      }
      setError(null);
      try {
        const data = await getStudentConversations(student.id, PAGE_SIZE, offset);
        setConversations((prev) => (offset === 0 ? data.conversations : [...prev, ...data.conversations]));
        setNextOffset(data.next_offset);
      } catch (err) {
        console.error(err);
        setError(err instanceof Error ? err.message : 'Failed to fetch conversations.');
      } finally {
        setIsInitialLoading(false);
        setIsLoadMore(false);
      }
    },
    [student]
  );

  useEffect(() => {
    if (!student) {
      setError('No student selected.');
      return;
    }
    fetchConversations(0);
    
    // Fetch persona for this student's user
    const fetchPersona = async () => {
      setPersonaLoading(true);
      try {
        const personaData = await getUserPersona(student.user_id);
        setPersona(personaData);
      } catch (err) {
        console.error('Failed to fetch persona:', err);
        // Don't show error to user - persona is optional
      } finally {
        setPersonaLoading(false);
      }
    };
    
    fetchPersona();
  }, [student, fetchConversations]);

  const handleLoadMore = () => {
    if (nextOffset == null || isLoadMore) {
      return;
    }
    fetchConversations(nextOffset);
  };

  if (!student) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 px-4">
        <div className="max-w-md w-full bg-white rounded-2xl shadow p-6 space-y-4 text-center">
          <p className="text-slate-700">No student selected.</p>
          <button
            onClick={() => navigate(-1)}
            className="inline-flex items-center justify-center rounded-full bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow hover:bg-indigo-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-indigo-500"
          >
            Back
          </button>
        </div>
      </div>
    );
  }

  const classLabelParts = [];
  if (classInfo.school) {
    classLabelParts.push(classInfo.school);
  }
  if (classInfo.grade) {
    classLabelParts.push(`Grade ${classInfo.grade}`);
  }
  if (classInfo.section) {
    classLabelParts.push(`Section ${classInfo.section}`);
  }
  const classLabel = classLabelParts.join(' · ');

  // Filter conversations based on the toggle
  const filteredConversations = showAfterSchoolOnly
    ? conversations.filter((conv) => isAfterSchoolHours(conv.created_at))
    : conversations;

  return (
    <div className="min-h-screen bg-slate-50 py-10 px-4">
      <div className="mx-auto flex w-full max-w-4xl flex-col gap-6">
        <div className="rounded-3xl bg-white p-6 shadow-lg shadow-slate-200">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <button
                  onClick={() => {
                    if (classInfo.school && classInfo.grade) {
                      navigate('/class-details', {
                        state: {
                          school: classInfo.school,
                          grade: classInfo.grade,
                          section: classInfo.section,
                        },
                      });
                    } else {
                      navigate(-1);
                    }
                  }}
                  className="text-sm font-semibold text-slate-600 transition hover:text-slate-900"
                >
                  ← Back to Class
                </button>
                {classInfo.school && classInfo.grade ? (
                  <button
                    type="button"
                    className="inline-flex items-center justify-center rounded-full border border-indigo-600 px-3 py-1.5 text-xs font-semibold text-indigo-600 shadow-sm transition hover:bg-indigo-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-indigo-500"
                    onClick={() =>
                      navigate('/teacher-dashboard', {
                        state: {
                          school: classInfo.school,
                          grade: classInfo.grade,
                          section: classInfo.section,
                        },
                      })
                    }
                  >
                    Dashboard
                  </button>
                ) : null}
              </div>
              <h1 className="mt-3 text-3xl font-semibold text-slate-900">{student.first_name}&rsquo;s conversations</h1>
              <p className="text-sm text-slate-500">History ordered by most recent chats first.</p>
              {classLabel && <p className="text-xs text-slate-500">{classLabel}</p>}
              
              {/* Checkbox for after-school hours filter */}
              <div className="mt-4">
                <label className="flex items-center gap-3 cursor-pointer group">
                  <div className="relative">
                    <input
                      type="checkbox"
                      checked={showAfterSchoolOnly}
                      onChange={(e) => setShowAfterSchoolOnly(e.target.checked)}
                      className="sr-only peer"
                    />
                    <div className="w-5 h-5 border-2 border-slate-300 rounded peer-checked:bg-indigo-600 peer-checked:border-indigo-600 transition-all flex items-center justify-center group-hover:border-indigo-400">
                      {showAfterSchoolOnly && (
                        <svg className="w-3.5 h-3.5 text-white" fill="none" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" viewBox="0 0 24 24" stroke="currentColor">
                          <path d="M5 13l4 4L19 7"></path>
                        </svg>
                      )}
                    </div>
                  </div>
                  <span className="text-sm font-medium text-slate-700 group-hover:text-slate-900 transition-colors">
                    Show after-school hours conversations only
                  </span>
                </label>
              </div>
            </div>
            <button
              type="button"
              className="inline-flex items-center justify-center rounded-full px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-indigo-200/60 transition bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 hover:opacity-90 focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-indigo-500 whitespace-nowrap"
              onClick={() => {
                navigate('/student-analysis', {
                  state: { student },
                });
              }}
            >
              Analyze Kid
            </button>
          </div>
        </div>

        <div className="rounded-3xl bg-white p-6 shadow-lg shadow-slate-200 space-y-6">
          {error && (
            <div className="rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700">
              {error}
            </div>
          )}

          {isInitialLoading ? (
            <p className="text-sm text-slate-500">Loading conversations...</p>
          ) : filteredConversations.length === 0 ? (
            <p className="text-sm text-slate-500">
              {showAfterSchoolOnly 
                ? 'No after-school hours conversations found.' 
                : 'No conversations yet.'}
            </p>
          ) : (
            <ul className="space-y-6">
              {filteredConversations.map((conversation) => (
                <li key={conversation.id} className="rounded-2xl border border-slate-100 p-5 shadow-sm">
                  <div className="flex flex-col gap-2 border-b border-slate-100 pb-4 sm:flex-row sm:items-center sm:justify-between">
                    <div>
                      <p className="text-lg font-semibold text-slate-900">
                        {conversation.title || 'Untitled conversation'}
                      </p>
                      <p className="text-xs uppercase tracking-wide text-slate-500">Conversation #{conversation.id}</p>
                    </div>
                    <div className="flex flex-col items-start sm:items-end gap-1">
                      {(() => {
                        const score = getLatestCuriosityScore(conversation.messages);
                        return score !== null ? (
                          <span className="inline-flex items-center gap-1.5 rounded-full bg-gradient-to-r from-amber-400 to-orange-500 px-3 py-1 text-sm font-semibold text-white shadow-sm">
                            ✨ Score: {score}
                          </span>
                        ) : null;
                      })()}
                      <p className="text-sm text-slate-500">
                        Last updated {new Date(conversation.updated_at).toLocaleString()}
                      </p>
                    </div>
                  </div>
                  {(() => {
                    const evaluation = conversation.evaluation;
                    const metrics = [
                      {
                        label: 'Depth',
                        value: evaluation?.depth ?? null,
                        formatter: formatOneDecimal,
                      },
                      {
                        label: 'Relevant Qs',
                        value: evaluation?.relevant_question_count ?? null,
                        formatter: formatInteger,
                      },
                      {
                        label: 'Attention',
                        value: evaluation?.attention_span ?? null,
                        formatter: formatOneDecimal,
                      },
                    ].filter((item) => item.value !== null && item.value !== undefined);

                    if (metrics.length === 0) {
                      return null;
                    }

                    return (
                      <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-600">
                        {metrics.map((item) => (
                          <span
                            key={item.label}
                            className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-3 py-1"
                          >
                            <span className="font-semibold text-slate-700">{item.label}:</span>
                            <span>{item.formatter(item.value as number)}</span>
                          </span>
                        ))}
                      </div>
                    );
                  })()}
                  <div className="mt-4 max-h-[40vh] space-y-4 overflow-y-auto pr-1">
                    {conversation.messages.length === 0 ? (
                      <p className="text-sm text-slate-500">No messages yet.</p>
                    ) : (
                      conversation.messages.map((message) => (
                        <div
                          key={message.id}
                          className={`flex flex-col ${
                            message.is_user ? 'items-start text-indigo-700' : 'items-end text-green-700'
                          }`}
                        >
                          <span className="text-xs uppercase font-semibold tracking-wide">
                            {message.is_user ? 'Kid' : 'Coach'}
                          </span>
                          <div
                            className={`mt-1 rounded-2xl px-4 py-2 shadow-sm ${
                              message.is_user ? 'bg-white border border-indigo-100' : 'bg-green-50 border border-green-100'
                            }`}
                          >
                            <p className="text-sm text-slate-800">{message.content}</p>
                            <p className="mt-1 text-xs text-slate-400">
                              {new Date(message.timestamp).toLocaleString()}
                            </p>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}

          {nextOffset !== null && conversations.length > 0 && (
            <button
              onClick={handleLoadMore}
              disabled={isLoadMore}
              className="inline-flex w-full items-center justify-center rounded-full bg-slate-900 px-6 py-3 text-sm font-semibold text-white shadow transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
            >
              {isLoadMore ? 'Loading...' : 'Load more conversations'}
            </button>
          )}
        </div>

        {/* User Persona Section - Dynamic rendering */}
        {!personaLoading && (() => {
          const personaData = getPersonaData(persona);
          if (!personaData) return null;
          
          // Filter out internal metadata keys (starting with _)
          const displayKeys = Object.keys(personaData).filter(key => !key.startsWith('_'));
          if (displayKeys.length === 0) return null;
          
          return (
            <div className="rounded-3xl bg-gradient-to-br from-purple-50 to-pink-50 p-6 shadow-lg shadow-slate-200">
              <h2 className="text-2xl font-semibold text-slate-900 mb-4 flex items-center gap-2">
                <span>🎯</span>
                <span>Learning Profile</span>
              </h2>
              <p className="text-xs text-slate-500 mb-4">
                Last updated: {persona ? new Date(persona.updated_at).toLocaleString() : ''}
              </p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {displayKeys.map((key) => {
                  const title = formatPersonaKey(key);
                  const emoji = getPersonaEmoji(key);
                  const value = personaData[key];
                  
                  // Convert value to string if it's not already
                  const displayValue = typeof value === 'object' 
                    ? JSON.stringify(value, null, 2)
                    : String(value);
                  
                  return (
                    <div key={key} className="bg-white/60 backdrop-blur-sm rounded-2xl p-4 border border-purple-100">
                      <h3 className="text-sm font-semibold text-purple-700 mb-2 flex items-center gap-2">
                        <span>{emoji}</span>
                        <span>{title}</span>
                      </h3>
                      <p className="text-sm text-slate-700 whitespace-pre-wrap">{displayValue}</p>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })()}
      </div>
    </div>
  );
};

export default TeacherConversationView;
