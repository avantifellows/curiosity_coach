import React, { useEffect, useMemo, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { StudentWithConversation } from '../types';
import { getClassTags, getStudentsForClass, updateStudentTags } from '../services/api';

interface ClassDetailsState {
  school?: string;
  grade?: number | string;
  section?: string;
}

const formatDateTime = (isoString?: string) => {
  if (!isoString) {
    return { date: '—', time: '' };
  }

  const date = new Date(isoString);
  return {
    date: date.toLocaleDateString(undefined, {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    }),
    time: date.toLocaleTimeString(undefined, {
      hour: '2-digit',
      minute: '2-digit',
    }),
  };
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

const ClassDetails: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const state = (location.state as ClassDetailsState) || {};

  const { school, grade, section } = state;
  const [students, setStudents] = useState<StudentWithConversation[] | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tagError, setTagError] = useState<string | null>(null);
  const [tagSuggestions, setTagSuggestions] = useState<string[]>([]);
  const [tagFilters, setTagFilters] = useState<string[]>([]);
  const [tagMode, setTagMode] = useState<'any' | 'all'>('any');
  const [tagFilterInput, setTagFilterInput] = useState('');
  const [tagDrafts, setTagDrafts] = useState<Record<number, string>>({});
  const [tagSaving, setTagSaving] = useState<Record<number, boolean>>({});

  const gradeNumber = useMemo(() => {
    if (typeof grade === 'number') {
      return grade;
    }
    if (typeof grade === 'string') {
      const parsed = Number(grade);
      return Number.isNaN(parsed) ? undefined : parsed;
    }
    return undefined;
  }, [grade]);

  useEffect(() => {
    if (!school || !gradeNumber || !section) {
      navigate('/teacher-view', { replace: true });
      return;
    }

    let isMounted = true;
    const fetchStudents = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const data = await getStudentsForClass(school, gradeNumber, section, tagFilters, tagMode);
        if (isMounted) {
          setStudents(data);
        }
      } catch (err) {
        console.error('Failed to fetch students for class:', err);
        if (isMounted) {
          setError('Failed to fetch students. Please try again.');
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    fetchStudents();

    return () => {
      isMounted = false;
    };
  }, [school, gradeNumber, section, tagFilters, tagMode, navigate]);

  useEffect(() => {
    if (!school || !gradeNumber || !section) {
      return;
    }

    let isMounted = true;
    const fetchTagSuggestions = async () => {
      try {
        const data = await getClassTags(school, gradeNumber, section);
        if (isMounted) {
          setTagSuggestions(data);
        }
      } catch (err) {
        console.error('Failed to fetch tag suggestions:', err);
      }
    };

    fetchTagSuggestions();

    return () => {
      isMounted = false;
    };
  }, [school, gradeNumber, section]);

  const normalizeTagInput = (value: string) => value.trim().replace(/\s+/g, ' ').toLowerCase();

  const addTagFilter = (rawTag: string) => {
    const normalized = normalizeTagInput(rawTag);
    if (!normalized || tagFilters.includes(normalized)) {
      return;
    }
    setTagFilters((prev) => [...prev, normalized]);
    setTagFilterInput('');
  };

  const removeTagFilter = (tag: string) => {
    setTagFilters((prev) => prev.filter((item) => item !== tag));
  };

  const handleFilterInputKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Enter' || event.key === ',') {
      event.preventDefault();
      addTagFilter(tagFilterInput);
    }
  };

  const matchesTagFilters = (tags: string[]) => {
    if (tagFilters.length === 0) {
      return true;
    }
    if (tagMode === 'all') {
      return tagFilters.every((tag) => tags.includes(tag));
    }
    return tagFilters.some((tag) => tags.includes(tag));
  };

  const updateStudentTagList = async (studentId: number, nextTags: string[]) => {
    setTagSaving((prev) => ({ ...prev, [studentId]: true }));
    setTagError(null);
    try {
      const updatedStudent = await updateStudentTags(studentId, nextTags);
      setStudents((prev) => {
        if (!prev) {
          return prev;
        }
        const updatedTags = updatedStudent.tags ?? [];
        if (tagFilters.length > 0 && !matchesTagFilters(updatedTags)) {
          return prev.filter((entry) => entry.student.id !== studentId);
        }
        return prev.map((entry) =>
          entry.student.id === studentId
            ? {
                ...entry,
                student: {
                  ...entry.student,
                  tags: updatedTags,
                },
              }
            : entry
        );
      });
      setTagSuggestions((prev) => {
        const merged = new Set(prev);
        (updatedStudent.tags ?? []).forEach((tag) => merged.add(tag));
        return Array.from(merged).sort();
      });
      setTagDrafts((prev) => ({ ...prev, [studentId]: '' }));
    } catch (err) {
      console.error('Failed to update tags:', err);
      setTagError('Failed to update tags. Please try again.');
    } finally {
      setTagSaving((prev) => ({ ...prev, [studentId]: false }));
    }
  };

  const handleAddTag = (studentId: number) => {
    const rawTag = tagDrafts[studentId] ?? '';
    const normalized = normalizeTagInput(rawTag);
    if (!normalized || !students) {
      return;
    }
    const entry = students.find((item) => item.student.id === studentId);
    if (!entry) {
      return;
    }
    const existingTags = entry.student.tags ?? [];
    if (existingTags.includes(normalized)) {
      setTagDrafts((prev) => ({ ...prev, [studentId]: '' }));
      return;
    }
    updateStudentTagList(studentId, [...existingTags, normalized]);
  };

  const handleRemoveTag = (studentId: number, tag: string) => {
    if (!students) {
      return;
    }
    const entry = students.find((item) => item.student.id === studentId);
    if (!entry) {
      return;
    }
    const existingTags = entry.student.tags ?? [];
    updateStudentTagList(
      studentId,
      existingTags.filter((item) => item !== tag)
    );
  };

  const hasClassInfo = Boolean(school || gradeNumber || section);
  const summaryChips = [
    { label: 'School', value: school, icon: '🏫' },
    { label: 'Grade', value: gradeNumber ? `Grade ${gradeNumber}` : undefined, icon: '📘' },
    { label: 'Section', value: section ? `Section ${section}` : undefined, icon: '✏️' },
  ].filter((chip) => Boolean(chip.value));

  const studentCountLabel = students
    ? `${students.length} Student${students.length === 1 ? '' : 's'}`
    : 'Students';

  type AggregatedTopic = {
    term: string;
    weight: number;
    total_weight: number;
    count: number;
    conversation_count: number;
  };

  const topTopics = useMemo(() => {
    if (!students) {
      return [];
    }

    const topicTotals = new Map<string, AggregatedTopic>();

    students.forEach(({ latest_conversation }) => {
      const topics = latest_conversation?.evaluation?.topics ?? [];
      topics.forEach((topic) => {
        if (!topic || !topic.term) {
          return;
        }
        const termKey = topic.term.trim().toLowerCase();
        if (!termKey) {
          return;
        }
        const weightContribution =
          typeof topic.total_weight === 'number' && !Number.isNaN(topic.total_weight)
            ? topic.total_weight
            : typeof topic.weight === 'number' && !Number.isNaN(topic.weight)
            ? topic.weight
            : 1;
        const countContribution =
          typeof topic.conversation_count === 'number' && topic.conversation_count > 0
            ? topic.conversation_count
            : typeof topic.count === 'number' && topic.count > 0
            ? topic.count
            : 1;

        const existing = topicTotals.get(termKey) ?? {
          term: topic.term,
          weight: 0,
          total_weight: 0,
          count: 0,
          conversation_count: 0,
        };

        existing.term = topic.term;
        existing.weight += weightContribution;
        existing.total_weight += weightContribution;
        existing.count += countContribution;
        existing.conversation_count += countContribution;
        topicTotals.set(termKey, existing);
      });
    });

    return Array.from(topicTotals.values())
      .sort((a, b) => {
        const weightDiff = (b.weight || 0) - (a.weight || 0);
        if (Math.abs(weightDiff) > 0.0001) {
          return weightDiff;
        }
        if (b.count !== a.count) {
          return b.count - a.count;
        }
        return a.term.localeCompare(b.term);
      })
      .slice(0, 6);
  }, [students]);

  return (
    <div className="min-h-screen bg-slate-50 py-12 px-4">
      <div className="mx-auto w-full max-w-4xl">
        <div className="rounded-3xl bg-white px-6 py-10 shadow-2xl shadow-slate-200 sm:px-10 space-y-10">
          <section className="space-y-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <button
                type="button"
                className="text-sm font-semibold text-slate-600 transition hover:text-slate-900"
                onClick={() => {
                  navigate('/teacher-dashboard', {
                    state: { school, grade: gradeNumber ?? grade, section },
                  });
                }}
              >
                ← Back to Dashboard
              </button>
              <button
                type="button"
                className="inline-flex items-center justify-center rounded-full border border-indigo-600 px-4 py-2 text-xs font-semibold text-indigo-600 shadow-sm transition hover:bg-indigo-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-indigo-500"
                onClick={() => {
                  navigate('/class-summary', {
                    state: { school, grade: gradeNumber ?? grade, section },
                  });
                }}
              >
                Class Summary
              </button>
            </div>
            <div className="space-y-3 text-center">
              <h1 className="text-4xl font-semibold text-slate-900">Class Details</h1>
              <div className="mx-auto h-1 w-20 rounded-full bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500" />
            </div>
            
          {/* Summary chips */}
          {hasClassInfo ? (
              <div className="flex flex-wrap items-center justify-center gap-3 text-sm font-medium text-slate-600">
                {summaryChips.map((chip) => (
                  <div
                    key={chip.label}
                    className="inline-flex items-center gap-2 rounded-full bg-slate-100/80 px-4 py-2 text-slate-700"
                  >
                    <span aria-hidden>{chip.icon}</span>
                    <span>{chip.value}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-slate-500">
                No class info provided. Return to the teacher view to enter details.
              </p>
            )}

            {topTopics.length > 0 && (
              <div className="flex flex-col items-center gap-2 text-sm text-slate-600">
                <p className="font-semibold text-slate-700">Top Topics (latest chats)</p>
                <div className="flex flex-wrap justify-center gap-2">
                  {topTopics.map((topic) => (
                    <span
                      key={topic.term.toLowerCase()}
                      className="inline-flex items-center gap-1 rounded-full bg-indigo-50 px-3 py-1 text-xs font-semibold text-indigo-700"
                    >
                      <span>{topic.term}</span>
                      {typeof topic.total_weight === 'number' && !Number.isNaN(topic.total_weight) ? (
                        <span className="text-[10px] text-indigo-500">{formatOneDecimal(topic.total_weight)}</span>
                      ) : typeof topic.weight === 'number' && !Number.isNaN(topic.weight) ? (
                        <span className="text-[10px] text-indigo-500">{formatOneDecimal(topic.weight)}</span>
                      ) : topic.count > 0 ? (
                        <span className="text-[10px] text-indigo-500">×{formatInteger(topic.count)}</span>
                      ) : null}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </section>

          <section className="space-y-4">
            <div className="flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <p className="text-lg font-semibold text-slate-900">{studentCountLabel}</p>
                <p className="text-sm text-slate-500">Open a student to view their conversations</p>
              </div>
            </div>

            <div className="flex flex-col gap-3 rounded-2xl border border-slate-200 bg-white/70 p-4">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-sm font-semibold text-slate-700">Filter tags</span>
                {tagFilters.length === 0 && (
                  <span className="text-xs text-slate-400">No filters applied</span>
                )}
              </div>
              <div className="flex flex-wrap items-center gap-2">
                {tagFilters.map((tag) => (
                  <span
                    key={`filter-${tag}`}
                    className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-3 py-1 text-[11px] font-medium text-emerald-700"
                  >
                    <span>{tag}</span>
                    <button
                      type="button"
                      className="text-[12px] leading-none text-emerald-500 transition hover:text-emerald-700"
                      onClick={() => removeTagFilter(tag)}
                      aria-label={`Remove filter tag ${tag}`}
                    >
                      ×
                    </button>
                  </span>
                ))}
                <input
                  value={tagFilterInput}
                  onChange={(event) => setTagFilterInput(event.target.value)}
                  onKeyDown={handleFilterInputKeyDown}
                  list="class-tag-suggestions"
                  placeholder="Type a tag and press Enter"
                  className="min-w-[180px] flex-1 rounded-full border border-slate-200 bg-white px-4 py-2 text-sm text-slate-700 shadow-sm focus:border-indigo-300 focus:outline-none focus:ring-2 focus:ring-indigo-200"
                />
                <button
                  type="button"
                  className="rounded-full border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-600 transition hover:border-indigo-200 hover:text-indigo-600"
                  onClick={() => setTagMode((prev) => (prev === 'any' ? 'all' : 'any'))}
                >
                  Match: {tagMode === 'any' ? 'Any' : 'All'}
                </button>
              </div>
            </div>

            <datalist id="class-tag-suggestions">
              {tagSuggestions.map((tag) => (
                <option key={`tag-suggestion-${tag}`} value={tag} />
              ))}
            </datalist>

            {isLoading && <p className="text-sm text-slate-500">Loading students...</p>}
            {error && <p className="text-sm text-red-600">{error}</p>}
            {tagError && <p className="text-sm text-red-600">{tagError}</p>}

            {!isLoading && !error && students && (
              <>
                {students.length === 0 ? (
                  <p className="text-sm text-slate-500">No students found for this class.</p>
                ) : (
                  <ul className="space-y-4">
                    {students.map(({ student, latest_conversation }) => {
                      const initials = (student.first_name || '?').charAt(0).toUpperCase();
                      const { date, time } = formatDateTime(latest_conversation?.updated_at);
                      const hasConversation = Boolean(latest_conversation);
                      const lastChatLabel = hasConversation ? latest_conversation?.title || 'New Chat' : 'No conversations yet';
                      const evaluation = latest_conversation?.evaluation;
                      const curiositySummary = latest_conversation?.curiosity_summary;
                      const conversationTopics = evaluation?.topics ?? [];
                      const studentTags = student.tags ?? [];
                      const divergentLabel =
                        evaluation?.divergent === true
                          ? 'Yes'
                          : evaluation?.divergent === false
                            ? 'No'
                            : null;
                      const studentRequestLabel = formatStudentRequest(evaluation?.student_request ?? null);

                      return (
                        <li
                          key={student.id}
                          className="flex flex-col gap-4 rounded-3xl bg-slate-50/80 p-5 shadow-md shadow-slate-200 sm:flex-row sm:items-center sm:justify-between"
                        >
                          <div className="flex items-start gap-4">
                            <div className="flex h-14 w-14 items-center justify-center rounded-full bg-indigo-100 text-lg font-semibold text-indigo-600">
                              {initials}
                            </div>
                            <div className="text-left">
                              <p className="text-xl font-semibold text-slate-900">{student.first_name}</p>
                              <p className="text-sm text-slate-500">Roll #{student.roll_number || '—'}</p>
                              <div className="mt-2 flex flex-wrap items-center gap-2">
                                {studentTags.map((tag) => (
                                  <span
                                    key={`${student.id}-${tag}`}
                                    className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-3 py-1 text-[11px] font-medium text-emerald-700"
                                  >
                                    <span>{tag}</span>
                                    <button
                                      type="button"
                                      className="text-[12px] leading-none text-emerald-500 transition hover:text-emerald-700"
                                      onClick={() => handleRemoveTag(student.id, tag)}
                                      aria-label={`Remove tag ${tag}`}
                                      disabled={tagSaving[student.id]}
                                    >
                                      ×
                                    </button>
                                  </span>
                                ))}
                                <div className="flex items-center gap-2">
                                  <input
                                    value={tagDrafts[student.id] ?? ''}
                                    onChange={(event) =>
                                      setTagDrafts((prev) => ({
                                        ...prev,
                                        [student.id]: event.target.value,
                                      }))
                                    }
                                    onKeyDown={(event) => {
                                      if (event.key === 'Enter' || event.key === ',') {
                                        event.preventDefault();
                                        handleAddTag(student.id);
                                      }
                                    }}
                                    list="class-tag-suggestions"
                                    placeholder="Add tag"
                                    className="w-32 rounded-full border border-slate-200 bg-white px-3 py-1 text-xs text-slate-600 shadow-sm focus:border-indigo-300 focus:outline-none focus:ring-2 focus:ring-indigo-100"
                                    disabled={tagSaving[student.id]}
                                  />
                                  <button
                                    type="button"
                                    className="rounded-lg border border-slate-200 px-3 py-1.5 text-[11px] font-semibold text-slate-500 transition hover:border-indigo-200 hover:text-indigo-600"
                                    onClick={() => handleAddTag(student.id)}
                                    disabled={tagSaving[student.id]}
                                  >
                                    Add
                                  </button>
                                </div>
                              </div>
                            </div>
                          </div>

                          <div className="flex flex-col items-start gap-3 sm:items-end">
                            <div className="text-sm text-slate-500">
                              <p className="font-semibold text-slate-700">Last Chat: {lastChatLabel}</p>
                              <p>{date}</p>
                              {time && <p className="text-xs">{time}</p>}
                            </div>
                            {hasConversation && (
                              <div className="flex w-full flex-col gap-2 text-xs text-slate-600 sm:text-right sm:text-sm">
                                {evaluation && (
                                  <div className="flex flex-wrap gap-3 sm:justify-end">
                                    <span className="font-semibold text-slate-700">Evaluation</span>
                                    <span>Depth: {formatOneDecimal(evaluation.depth)}</span>
                                    <span>Relevant Qs: {formatInteger(evaluation.relevant_question_count)}</span>
                                    <span>Attention (min): {formatOneDecimal(evaluation.attention_span)}</span>
                                  </div>
                                )}
                                {(divergentLabel || studentRequestLabel) && (
                                  <div className="flex flex-wrap gap-3 sm:justify-end">
                                    <span className="font-semibold text-slate-700">Signals</span>
                                    {divergentLabel && <span>Divergent: {divergentLabel}</span>}
                                    {studentRequestLabel && <span>Request: {studentRequestLabel}</span>}
                                  </div>
                                )}
                                {curiositySummary && (
                                  <div className="flex flex-wrap gap-3 sm:justify-end">
                                    <span className="font-semibold text-slate-700">Curiosity</span>
                                    <span>Avg: {formatOneDecimal(curiositySummary.average)}</span>
                                    <span>Latest: {formatInteger(curiositySummary.latest)}</span>
                                  </div>
                                )}
                                {conversationTopics.length > 0 && (
                                  <div className="flex flex-wrap gap-2 sm:justify-end">
                                    {conversationTopics.slice(0, 3).map((topic) => (
                                      <span
                                        key={`${latest_conversation?.id ?? 'topic'}-${topic.term}`}
                                        className="inline-flex items-center gap-1 rounded-full bg-indigo-50 px-3 py-1 text-[11px] font-medium text-indigo-600"
                                      >
                                        <span>{topic.term}</span>
                                        {typeof topic.weight === 'number' && !Number.isNaN(topic.weight) ? (
                                          <span className="text-[10px] text-indigo-400">{formatOneDecimal(topic.weight)}</span>
                                        ) : topic.count ? (
                                          <span className="text-[10px] text-indigo-400">×{formatInteger(topic.count)}</span>
                                        ) : null}
                                      </span>
                                    ))}
                                  </div>
                                )}
                              </div>
                            )}
                            <button
                              type="button"
                              className="inline-flex items-center justify-center rounded-full px-5 py-2 text-sm font-semibold text-white shadow-lg shadow-indigo-200/60 transition bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 hover:opacity-90 focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-indigo-500"
                              onClick={() =>
                                navigate('/class-conversation', {
                                  state: {
                                    student,
                                    school,
                                    grade: gradeNumber ?? grade,
                                    section,
                                  },
                                })
                              }
                            >
                              View Conversations
                            </button>
                          </div>
                        </li>
                      );
                    })}
                  </ul>
                )}
              </>
            )}
          </section>
        </div>
      </div>
    </div>
  );
};

export default ClassDetails;
