import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { ConversationWithMessages, Student, UserPersona, UserPersonaData } from '../types';
import {
  getClassTags,
  getClassConversationTags,
  getConversationLookup,
  getStudentConversations,
  getStudentsForClass,
  getUserPersona,
  updateStudentConversationTags,
  updateStudentTags
} from '../services/api';

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

const formatStudentRequest = (value?: string | null) => {
  if (!value) {
    return null;
  }
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  return trimmed.charAt(0).toUpperCase() + trimmed.slice(1);
};

const parseIdParam = (value: string | null): number | null => {
  if (!value) {
    return null;
  }
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed <= 0) {
    return null;
  }
  return parsed;
};


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
  const searchParams = useMemo(() => new URLSearchParams(location.search), [location.search]);
  const dayParam = searchParams.get('day') || null;
  const studentId = parseIdParam(searchParams.get('student_id'));
  const highlightConversationId = parseIdParam(searchParams.get('conversation_id'));

  const [student, setStudent] = useState<Student | null>(state.student ?? null);
  const [dayFilter, setDayFilter] = useState<string | null>(dayParam);

  const classInfo = useMemo(() => {
    const school = state.school ?? searchParams.get('school') ?? student?.school ?? undefined;
    const gradeParam = state.grade ?? searchParams.get('grade') ?? student?.grade;
    const gradeValue = typeof gradeParam === 'number' ? gradeParam : Number(gradeParam);
    const grade = Number.isNaN(gradeValue) ? undefined : gradeValue;
    const section = state.section ?? searchParams.get('section') ?? student?.section ?? undefined;
    return { school, grade, section };
  }, [state.grade, state.school, state.section, searchParams, student]);
  const [conversations, setConversations] = useState<ConversationWithMessages[]>([]);
  const [nextOffset, setNextOffset] = useState<number | null>(null);
  const [isInitialLoading, setIsInitialLoading] = useState(false);
  const [isLoadMore, setIsLoadMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [persona, setPersona] = useState<UserPersona | null>(null);
  const [personaLoading, setPersonaLoading] = useState(false);
  const [showAfterSchoolOnly, setShowAfterSchoolOnly] = useState(false);
  const [studentLoading, setStudentLoading] = useState(false);
  const [tagSuggestions, setTagSuggestions] = useState<string[]>([]);
  const [tagDraft, setTagDraft] = useState('');
  const [tagSaving, setTagSaving] = useState(false);
  const [tagError, setTagError] = useState<string | null>(null);
  const [conversationTagSuggestions, setConversationTagSuggestions] = useState<string[]>([]);
  const [conversationTagFilters, setConversationTagFilters] = useState<string[]>([]);
  const [conversationTagMode, setConversationTagMode] = useState<'any' | 'all'>('any');
  const [conversationTagFilterInput, setConversationTagFilterInput] = useState('');
  const [conversationTagDrafts, setConversationTagDrafts] = useState<Record<number, string>>({});
  const [conversationTagSaving, setConversationTagSaving] = useState<Record<number, boolean>>({});
  const [conversationTagError, setConversationTagError] = useState<string | null>(null);
  const [selectedConversationId, setSelectedConversationId] = useState<number | null>(highlightConversationId);
  const [lookupLoading, setLookupLoading] = useState(false);
  const [autoLoadForHighlight, setAutoLoadForHighlight] = useState(Boolean(highlightConversationId));
  const [appliedHighlightId, setAppliedHighlightId] = useState<number | null>(null);

  useEffect(() => {
    setDayFilter(dayParam);
  }, [dayParam]);

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
        const limit = highlightConversationId || dayFilter ? 50 : PAGE_SIZE;
        const data = await getStudentConversations(
          student.id,
          limit,
          offset,
          dayFilter,
          conversationTagFilters,
          conversationTagMode
        );
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
    [student, dayFilter, conversationTagFilters, conversationTagMode, highlightConversationId]
  );

  const fetchStudentById = useCallback(async () => {
    if (!studentId || !classInfo.school || !classInfo.grade) {
      setError('No student selected.');
      return;
    }
    setStudentLoading(true);
    try {
      const roster = await getStudentsForClass(classInfo.school!, classInfo.grade!, classInfo.section ?? null);
      const match = roster.find((entry) => entry.student.id === studentId);
      if (match) {
        setStudent(match.student);
      } else {
        setError('Student not found for this class.');
      }
    } catch (err) {
      console.error('Failed to fetch student details:', err);
      setError('Failed to load student details.');
    } finally {
      setStudentLoading(false);
    }
  }, [classInfo.grade, classInfo.school, classInfo.section, studentId]);

  useEffect(() => {
    if (student) {
      return;
    }
    if (highlightConversationId) {
      if (lookupLoading) {
        return;
      }
      const fetchByConversation = async () => {
        setLookupLoading(true);
        setError(null);
        try {
          const lookup = await getConversationLookup(highlightConversationId);
          setStudent(lookup.student);
          const nextParams = new URLSearchParams(location.search);
          nextParams.set('student_id', String(lookup.student.id));
          nextParams.set('school', lookup.student.school);
          nextParams.set('grade', String(lookup.student.grade));
          if (lookup.student.section) {
            nextParams.set('section', lookup.student.section);
          } else {
            nextParams.delete('section');
          }
          navigate({ pathname: location.pathname, search: nextParams.toString() }, { replace: true, state });
        } catch (err) {
          console.error('Failed to lookup conversation:', err);
          setError('Failed to resolve conversation to a student.');
          if (studentId && classInfo.school && classInfo.grade) {
            await fetchStudentById();
          }
        } finally {
          setLookupLoading(false);
        }
      };
      fetchByConversation();
      return;
    }

    fetchStudentById();
  }, [
    student,
    studentId,
    classInfo.school,
    classInfo.grade,
    classInfo.section,
    highlightConversationId,
    lookupLoading,
    location.search,
    navigate,
    state,
    fetchStudentById,
  ]);

  useEffect(() => {
    if (!student) {
      return;
    }
    const fetchPersona = async () => {
      setPersonaLoading(true);
      try {
        const personaData = await getUserPersona(student.user_id);
        setPersona(personaData);
      } catch (err) {
        console.error('Failed to fetch persona:', err);
      } finally {
        setPersonaLoading(false);
      }
    };
    fetchPersona();
  }, [student]);

  useEffect(() => {
    if (!student) {
      return;
    }
    fetchConversations(0);
  }, [student, dayFilter, conversationTagFilters, conversationTagMode, fetchConversations]);

  useEffect(() => {
    if (!classInfo.school || !classInfo.grade) {
      return;
    }

    let isMounted = true;
    const fetchTags = async () => {
      try {
        const tags = await getClassTags(classInfo.school!, classInfo.grade!, classInfo.section ?? null);
        if (isMounted) {
          setTagSuggestions(tags);
        }
      } catch (err) {
        console.error('Failed to fetch tag suggestions:', err);
      }
    };

    fetchTags();

    return () => {
      isMounted = false;
    };
  }, [classInfo.school, classInfo.grade, classInfo.section]);

  useEffect(() => {
    if (!classInfo.school || !classInfo.grade) {
      return;
    }

    let isMounted = true;
    const fetchConversationTags = async () => {
      try {
        const tags = await getClassConversationTags(
          classInfo.school!,
          classInfo.grade!,
          classInfo.section ?? null
        );
        if (isMounted) {
          setConversationTagSuggestions(tags);
        }
      } catch (err) {
        console.error('Failed to fetch conversation tag suggestions:', err);
      }
    };

    fetchConversationTags();

    return () => {
      isMounted = false;
    };
  }, [classInfo.school, classInfo.grade, classInfo.section]);

  const normalizeTagInput = (value: string) => value.trim().replace(/\s+/g, ' ').toLowerCase();

  const updateStudentTagList = async (nextTags: string[]) => {
    if (!student) {
      return;
    }
    setTagSaving(true);
    setTagError(null);
    try {
      const updatedStudent = await updateStudentTags(student.id, nextTags);
      setStudent((prev) => (prev ? { ...prev, tags: updatedStudent.tags ?? [] } : prev));
      setTagDraft('');
      setTagSuggestions((prev) => {
        const merged = new Set(prev);
        (updatedStudent.tags ?? []).forEach((tag) => merged.add(tag));
        return Array.from(merged).sort();
      });
    } catch (err) {
      console.error('Failed to update tags:', err);
      setTagError('Failed to update tags. Please try again.');
    } finally {
      setTagSaving(false);
    }
  };

  const handleAddTag = () => {
    if (!student) {
      return;
    }
    const normalized = normalizeTagInput(tagDraft);
    if (!normalized) {
      return;
    }
    const existing = student.tags ?? [];
    if (existing.includes(normalized)) {
      setTagDraft('');
      return;
    }
    updateStudentTagList([...existing, normalized]);
  };

  const handleRemoveTag = (tag: string) => {
    if (!student) {
      return;
    }
    const existing = student.tags ?? [];
    updateStudentTagList(existing.filter((item) => item !== tag));
  };

  const addConversationTagFilter = (rawTag: string) => {
    const normalized = normalizeTagInput(rawTag);
    if (!normalized || conversationTagFilters.includes(normalized)) {
      return;
    }
    setConversationTagFilters((prev) => [...prev, normalized]);
    setConversationTagFilterInput('');
  };

  const removeConversationTagFilter = (tag: string) => {
    setConversationTagFilters((prev) => prev.filter((item) => item !== tag));
  };

  const updateConversationTagList = async (conversationId: number, nextTags: string[]) => {
    if (!student) {
      return;
    }
    setConversationTagSaving((prev) => ({ ...prev, [conversationId]: true }));
    setConversationTagError(null);
    try {
      const updatedConversation = await updateStudentConversationTags(student.id, conversationId, nextTags);
      setConversations((prev) =>
        prev.map((conversation) =>
          conversation.id === conversationId
            ? { ...conversation, tags: updatedConversation.tags ?? [] }
            : conversation
        )
      );
      setConversationTagDrafts((prev) => ({ ...prev, [conversationId]: '' }));
      setConversationTagSuggestions((prev) => {
        const merged = new Set(prev);
        (updatedConversation.tags ?? []).forEach((tag) => merged.add(tag));
        return Array.from(merged).sort();
      });
    } catch (err) {
      console.error('Failed to update conversation tags:', err);
      setConversationTagError('Failed to update conversation tags. Please try again.');
    } finally {
      setConversationTagSaving((prev) => ({ ...prev, [conversationId]: false }));
    }
  };

  const handleAddConversationTag = (conversationId: number) => {
    const rawTag = conversationTagDrafts[conversationId] ?? '';
    const normalized = normalizeTagInput(rawTag);
    if (!normalized) {
      return;
    }
    const conversation = conversations.find((item) => item.id === conversationId);
    const existing = conversation?.tags ?? [];
    if (existing.includes(normalized)) {
      setConversationTagDrafts((prev) => ({ ...prev, [conversationId]: '' }));
      return;
    }
    updateConversationTagList(conversationId, [...existing, normalized]);
  };

  const handleRemoveConversationTag = (conversationId: number, tag: string) => {
    const conversation = conversations.find((item) => item.id === conversationId);
    const existing = conversation?.tags ?? [];
    updateConversationTagList(
      conversationId,
      existing.filter((item) => item !== tag)
    );
  };

  const handleLoadMore = () => {
    if (nextOffset == null || isLoadMore) {
      return;
    }
    fetchConversations(nextOffset);
  };

  // Filter conversations based on the toggle
  const filteredConversations = showAfterSchoolOnly
    ? conversations.filter((conv) => isAfterSchoolHours(conv.created_at))
    : conversations;
  const studentTags = student?.tags ?? [];
  const selectedConversation = filteredConversations.find((conv) => conv.id === selectedConversationId) ?? null;

  useEffect(() => {
    if (!highlightConversationId) {
      return;
    }
    if (appliedHighlightId === highlightConversationId) {
      return;
    }
    setSelectedConversationId(highlightConversationId);
    setAutoLoadForHighlight(true);
    setAppliedHighlightId(highlightConversationId);
  }, [highlightConversationId, appliedHighlightId]);

  useEffect(() => {
    if (filteredConversations.length === 0) {
      if (!highlightConversationId) {
        setSelectedConversationId(null);
      }
      return;
    }
    if (!selectedConversationId && !highlightConversationId) {
      setSelectedConversationId(filteredConversations[0].id);
      return;
    }
    const exists = filteredConversations.some((conv) => conv.id === selectedConversationId);
    if (!exists && !highlightConversationId) {
      setSelectedConversationId(filteredConversations[0].id);
    }
  }, [filteredConversations, selectedConversationId, highlightConversationId]);

  useEffect(() => {
    if (!highlightConversationId || !autoLoadForHighlight) {
      return;
    }
    const found = filteredConversations.some((conv) => conv.id === highlightConversationId);
    if (found) {
      setAutoLoadForHighlight(false);
      return;
    }
    if (nextOffset == null || isLoadMore || isInitialLoading) {
      if (nextOffset == null) {
        setAutoLoadForHighlight(false);
      }
      return;
    }
    fetchConversations(nextOffset);
  }, [
    highlightConversationId,
    autoLoadForHighlight,
    filteredConversations,
    nextOffset,
    isLoadMore,
    isInitialLoading,
    fetchConversations,
  ]);

  const handleSelectConversation = (conversationId: number) => {
    setSelectedConversationId(conversationId);
    const nextParams = new URLSearchParams(location.search);
    nextParams.set('conversation_id', String(conversationId));
    navigate({ pathname: location.pathname, search: nextParams.toString() }, { replace: true, state });
  };

  if (!student) {
    const emptyStateMessage =
      error ?? (studentLoading || lookupLoading ? 'Loading student details...' : 'No student selected.');
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 px-4">
        <div className="max-w-md w-full bg-white rounded-2xl shadow p-6 space-y-4 text-center">
          <p className="text-slate-700">{emptyStateMessage}</p>
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
              {dayFilter && (
                <div className="mt-3 inline-flex items-center gap-2 rounded-full bg-indigo-50 px-3 py-1 text-xs font-semibold text-indigo-700">
                  <span>Filtered to {new Date(dayFilter).toLocaleDateString()}</span>
                  <button
                    type="button"
                    className="text-[11px] font-semibold text-indigo-600 hover:text-indigo-800"
                    onClick={() => {
                      setDayFilter(null);
                      const nextParams = new URLSearchParams(location.search);
                      nextParams.delete('day');
                      nextParams.delete('conversation_id');
                      navigate(
                        { pathname: location.pathname, search: nextParams.toString() },
                        { replace: true, state }
                      );
                    }}
                  >
                    Clear
                  </button>
                </div>
              )}

              <div className="mt-4 flex flex-wrap items-center gap-2">
                <span className="text-xs font-semibold text-slate-600">Tags</span>
                {studentTags.map((tag) => (
                  <span
                    key={`student-tag-${tag}`}
                    className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-3 py-1 text-[11px] font-medium text-emerald-700"
                  >
                    <span>{tag}</span>
                    <button
                      type="button"
                      className="text-[12px] leading-none text-emerald-500 transition hover:text-emerald-700"
                      onClick={() => handleRemoveTag(tag)}
                      aria-label={`Remove tag ${tag}`}
                      disabled={tagSaving}
                    >
                      ×
                    </button>
                  </span>
                ))}
                <div className="flex items-center gap-2">
                  <input
                    value={tagDraft}
                    onChange={(event) => setTagDraft(event.target.value)}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter' || event.key === ',') {
                        event.preventDefault();
                        handleAddTag();
                      }
                    }}
                    list="student-tag-suggestions"
                    placeholder="Add tag"
                    className="w-36 rounded-full border border-slate-200 bg-white px-3 py-1 text-xs text-slate-600 shadow-sm focus:border-indigo-300 focus:outline-none focus:ring-2 focus:ring-indigo-100"
                    disabled={tagSaving}
                  />
                  <button
                    type="button"
                    className="rounded-lg border border-slate-200 px-3 py-1.5 text-[11px] font-semibold text-slate-500 transition hover:border-indigo-200 hover:text-indigo-600"
                    onClick={handleAddTag}
                    disabled={tagSaving}
                  >
                    Add
                  </button>
                </div>
              </div>
              {tagError && <p className="mt-2 text-xs text-red-600">{tagError}</p>}
              
              <div className="mt-4 rounded-2xl border border-slate-100 bg-slate-50 px-3 py-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-xs font-semibold text-slate-600">Conversation tags</span>
                  <button
                    type="button"
                    className="text-[11px] font-semibold text-indigo-600 hover:text-indigo-800"
                    onClick={() =>
                      setConversationTagMode((prev) => (prev === 'any' ? 'all' : 'any'))
                    }
                  >
                    Match: {conversationTagMode === 'any' ? 'Any' : 'All'}
                  </button>
                </div>
                <div className="mt-2 flex flex-wrap gap-2">
                  {conversationTagFilters.map((tag) => (
                    <span
                      key={`conversation-filter-${tag}`}
                      className="inline-flex items-center gap-1 rounded-full bg-indigo-50 px-3 py-1 text-[11px] font-semibold text-indigo-700"
                    >
                      <span>{tag}</span>
                      <button
                        type="button"
                        className="text-[12px] leading-none text-indigo-500 hover:text-indigo-700"
                        onClick={() => removeConversationTagFilter(tag)}
                        aria-label={`Remove filter tag ${tag}`}
                      >
                        ×
                      </button>
                    </span>
                  ))}
                  <input
                    value={conversationTagFilterInput}
                    onChange={(event) => setConversationTagFilterInput(event.target.value)}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter' || event.key === ',') {
                        event.preventDefault();
                        addConversationTagFilter(conversationTagFilterInput);
                      }
                    }}
                    list="conversation-tag-suggestions"
                    placeholder="Add filter"
                    className="w-32 rounded-full border border-slate-200 bg-white px-3 py-1 text-xs text-slate-600 shadow-sm focus:border-indigo-300 focus:outline-none focus:ring-2 focus:ring-indigo-100"
                  />
                </div>
                {conversationTagError && (
                  <p className="mt-2 text-xs text-red-600">{conversationTagError}</p>
                )}
              </div>

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

        <datalist id="student-tag-suggestions">
          {tagSuggestions.map((tag) => (
            <option key={`student-tag-suggestion-${tag}`} value={tag} />
          ))}
        </datalist>
        <datalist id="conversation-tag-suggestions">
          {conversationTagSuggestions.map((tag) => (
            <option key={`conversation-tag-suggestion-${tag}`} value={tag} />
          ))}
        </datalist>

        <div className="rounded-3xl bg-white p-6 shadow-lg shadow-slate-200">
          {error && (
            <div className="rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700">
              {error}
            </div>
          )}

          {isInitialLoading ? (
            <p className="text-sm text-slate-500">Loading conversations...</p>
          ) : filteredConversations.length === 0 ? (
            <p className="text-sm text-slate-500">
              {conversationTagFilters.length > 0
                ? 'No conversations match these tags.'
                : (showAfterSchoolOnly 
                  ? 'No after-school hours conversations found.' 
                  : 'No conversations yet.')}
            </p>
          ) : (
            <div className="grid gap-6 lg:grid-cols-[320px_minmax(0,1fr)]">
              <div className="rounded-2xl border border-slate-100 bg-slate-50/60 p-3">
                <div className="mb-3 flex items-center justify-between px-2">
                  <h2 className="text-sm font-semibold text-slate-700">All conversations</h2>
                  <span className="text-xs text-slate-500">{filteredConversations.length} total</span>
                </div>
                <div className="max-h-[70vh] space-y-2 overflow-y-auto pr-1">
                  {filteredConversations.map((conversation) => {
                    const isSelected = selectedConversationId === conversation.id;
                    const score = getLatestCuriosityScore(conversation.messages);
                    return (
                      <button
                        key={conversation.id}
                        type="button"
                        onClick={() => handleSelectConversation(conversation.id)}
                        className={`w-full rounded-xl border px-3 py-3 text-left shadow-sm transition ${
                          isSelected
                            ? 'border-indigo-200 bg-white shadow-indigo-100'
                            : 'border-transparent bg-white/70 hover:border-indigo-100 hover:bg-white'
                        }`}
                      >
                        <div className="flex items-center justify-between gap-2">
                          <p className="text-sm font-semibold text-slate-900">
                            {conversation.title || 'Untitled conversation'}
                          </p>
                          {score !== null && (
                            <span className="inline-flex items-center rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-semibold text-amber-700">
                              Score {score}
                            </span>
                          )}
                        </div>
                        <p className="mt-1 text-[11px] text-slate-500">
                          #{conversation.id} · {new Date(conversation.updated_at).toLocaleDateString()}
                        </p>
                        {(conversation.tags ?? []).length > 0 && (
                          <div className="mt-2 flex flex-wrap gap-1">
                            {(conversation.tags ?? []).slice(0, 3).map((tag) => (
                              <span
                                key={`${conversation.id}-${tag}-chip`}
                                className="rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-medium text-emerald-700"
                              >
                                {tag}
                              </span>
                            ))}
                            {(conversation.tags ?? []).length > 3 && (
                              <span className="text-[10px] text-slate-400">
                                +{(conversation.tags ?? []).length - 3}
                              </span>
                            )}
                          </div>
                        )}
                      </button>
                    );
                  })}
                </div>

                {nextOffset !== null && conversations.length > 0 && (
                  <button
                    onClick={handleLoadMore}
                    disabled={isLoadMore}
                    className="mt-3 inline-flex w-full items-center justify-center rounded-full bg-slate-900 px-4 py-2 text-xs font-semibold text-white shadow transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
                  >
                    {isLoadMore ? 'Loading...' : 'Load more'}
                  </button>
                )}
              </div>

              <div className="rounded-2xl border border-slate-100 bg-white p-5 shadow-sm">
                {!selectedConversation ? (
                  <p className="text-sm text-slate-500">Select a conversation to view its messages.</p>
                ) : (
                  (() => {
                    const evaluation = selectedConversation.evaluation;
                    const conversationTags = selectedConversation.tags ?? [];
                    const divergentLabel =
                      evaluation?.divergent === true
                        ? 'Yes'
                        : evaluation?.divergent === false
                          ? 'No'
                          : null;
                    const studentRequestLabel = formatStudentRequest(evaluation?.student_request ?? null);
                    return (
                      <div className="flex h-[82vh] flex-col">
                        <div className="flex flex-col gap-2 border-b border-slate-100 pb-4 sm:flex-row sm:items-center sm:justify-between">
                          <div>
                            <p className="text-lg font-semibold text-slate-900">
                              {selectedConversation.title || 'Untitled conversation'}
                            </p>
                            <p className="text-xs uppercase tracking-wide text-slate-500">
                              Conversation #{selectedConversation.id}
                            </p>
                          </div>
                          <div className="flex flex-col items-start sm:items-end gap-1">
                            {(() => {
                              const score = getLatestCuriosityScore(selectedConversation.messages);
                              return score !== null ? (
                                <span className="inline-flex items-center gap-1.5 rounded-full bg-gradient-to-r from-amber-400 to-orange-500 px-3 py-1 text-sm font-semibold text-white shadow-sm">
                                  ✨ Score: {score}
                                </span>
                              ) : null;
                            })()}
                            <p className="text-sm text-slate-500">
                              Last updated {new Date(selectedConversation.updated_at).toLocaleString()}
                            </p>
                          </div>
                        </div>

                        {(() => {
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
                              label: 'Attention (min)',
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

                        {(divergentLabel || studentRequestLabel) && (
                          <div className="mt-2 flex flex-wrap gap-2 text-xs text-slate-600">
                            {divergentLabel && (
                              <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-3 py-1">
                                <span className="font-semibold text-slate-700">Divergent:</span>
                                <span>{divergentLabel}</span>
                              </span>
                            )}
                            {studentRequestLabel && (
                              <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-3 py-1">
                                <span className="font-semibold text-slate-700">Request:</span>
                                <span>{studentRequestLabel}</span>
                              </span>
                            )}
                          </div>
                        )}

                        <div className="mt-3 flex flex-wrap items-center gap-2">
                          <span className="text-xs font-semibold text-slate-600">Tags</span>
                          {conversationTags.map((tag) => (
                            <span
                              key={`${selectedConversation.id}-${tag}`}
                              className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-3 py-1 text-[11px] font-medium text-emerald-700"
                            >
                              <span>{tag}</span>
                              <button
                                type="button"
                                className="text-[12px] leading-none text-emerald-500 transition hover:text-emerald-700"
                                onClick={() => handleRemoveConversationTag(selectedConversation.id, tag)}
                                aria-label={`Remove tag ${tag}`}
                                disabled={conversationTagSaving[selectedConversation.id]}
                              >
                                ×
                              </button>
                            </span>
                          ))}
                          <div className="flex items-center gap-2">
                            <input
                              value={conversationTagDrafts[selectedConversation.id] ?? ''}
                              onChange={(event) =>
                                setConversationTagDrafts((prev) => ({
                                  ...prev,
                                  [selectedConversation.id]: event.target.value,
                                }))
                              }
                              onKeyDown={(event) => {
                                if (event.key === 'Enter' || event.key === ',') {
                                  event.preventDefault();
                                  handleAddConversationTag(selectedConversation.id);
                                }
                              }}
                              list="conversation-tag-suggestions"
                              placeholder="Add tag"
                              className="w-32 rounded-full border border-slate-200 bg-white px-3 py-1 text-xs text-slate-600 shadow-sm focus:border-indigo-300 focus:outline-none focus:ring-2 focus:ring-indigo-100"
                              disabled={conversationTagSaving[selectedConversation.id]}
                            />
                            <button
                              type="button"
                              className="rounded-lg border border-slate-200 px-3 py-1.5 text-[11px] font-semibold text-slate-500 transition hover:border-indigo-200 hover:text-indigo-600"
                              onClick={() => handleAddConversationTag(selectedConversation.id)}
                              disabled={conversationTagSaving[selectedConversation.id]}
                            >
                              Add
                            </button>
                          </div>
                        </div>

                        <div className="mt-4 flex-1 space-y-4 overflow-y-auto pr-1">
                          {selectedConversation.messages.length === 0 ? (
                            <p className="text-sm text-slate-500">No messages yet.</p>
                          ) : (
                            selectedConversation.messages.map((message) => (
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
                      </div>
                    );
                  })()
                )}
              </div>
            </div>
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
