import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { StudentWithConversation, ConversationWithMessages } from '../types';
import {
  getStudentsForClass,
  analyzeClassConversations,
  getAnalysisJobStatus,
} from '../services/api';
import { AnalysisStatus } from '../types';
import parse from 'html-react-parser';

// Helper to detect if an error is likely a timeout (API Gateway 30s limit)
const isTimeoutError = (err: unknown): boolean => {
  if (!axios.isAxiosError(err)) return false;
  const status = err.response?.status;
  // 503 = Service Unavailable (often from Lambda/API Gateway timeout)
  // 504 = Gateway Timeout
  return err.code === 'ECONNABORTED' || status === 503 || status === 504 || !err.response;
};

// AnalysisLoading component with informative messaging
const AnalysisLoading: React.FC<{ message?: string; subtext?: string }> = ({ 
  message = "Preparing analysis...",
  subtext,
}) => {
  return (
    <div className="flex flex-col items-center justify-center py-12 px-4">
      <div className="text-center space-y-2">
        <p className="text-lg font-medium text-slate-700 animate-pulse">
          {message}
        </p>
        {subtext && (
          <p className="text-sm text-slate-500">{subtext}</p>
        )}
      </div>
    </div>
  );
};

interface ClassSummaryState {
  school?: string;
  grade?: number | string;
  section?: string;
}

interface ConversationWithStudent extends ConversationWithMessages {
  student_id: number;
  student_name: string;
  student_roll_number: number;
}

const ClassSummary: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const state = (location.state as ClassSummaryState) || {};

  const { school, grade, section } = state;
  const [students, setStudents] = useState<StudentWithConversation[] | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<string | null>(null);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [analysisStatus, setAnalysisStatus] = useState<AnalysisStatus>('ready');
  const [jobId, setJobId] = useState<string | null>(null);
  const [computedAt, setComputedAt] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const isAnalysisInProgress = analysisStatus === 'queued' || analysisStatus === 'running';
  const showAnalysisLoading = isAnalysisInProgress && !analysis;

  const isMountedRef = useRef(true);
  const pollTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      if (pollTimeoutRef.current) clearTimeout(pollTimeoutRef.current);
    };
  }, []);

  const stopPolling = useCallback(() => {
    if (pollTimeoutRef.current) {
      clearTimeout(pollTimeoutRef.current);
      pollTimeoutRef.current = null;
    }
  }, []);

  const pollJob = useCallback(
    async (job: string) => {
      if (!isMountedRef.current) {
        return;
      }

      try {
        const data = await getAnalysisJobStatus(job);
        if (!isMountedRef.current) {
          return;
        }

        const nextStatus: AnalysisStatus =
          data.analysis_status ?? (data.status === 'failed' ? 'failed' : data.status === 'completed' ? 'ready' : 'running');

        if (data.analysis !== undefined) {
          setAnalysis(data.analysis ?? null);
        }
        if (data.computed_at) {
          setComputedAt(data.computed_at);
        }

        if (data.status === 'failed' || nextStatus === 'failed') {
          setAnalysisStatus('failed');
          setAnalysisError(data.error_message ?? 'Analysis failed. Please try again.');
          setJobId(null);
          stopPolling();
          return;
        }

        if (data.status === 'completed' || nextStatus === 'ready') {
          setAnalysisStatus('ready');
          setAnalysisError(null);
          setJobId(null);
          stopPolling();
          return;
        }

        setAnalysisStatus(nextStatus);
        pollTimeoutRef.current = setTimeout(() => {
          pollJob(job);
        }, 4000);
      } catch (err) {
        if (!isMountedRef.current) {
          return;
        }
        console.error('Failed to poll class analysis job:', err);
        setAnalysisStatus('failed');
        setAnalysisError(err instanceof Error ? err.message : 'Failed to fetch analysis status.');
        setJobId(null);
        stopPolling();
      }
    },
    [stopPolling]
  );

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
        const data = await getStudentsForClass(school, gradeNumber, section);
        if (isMounted) {
          setStudents(data);
        }
      } catch (err) {
        console.error('Failed to fetch students for class:', err);
        if (isMounted) {
          setError('Failed to fetch conversations. Please try again.');
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
  }, [school, gradeNumber, section, navigate]);

  const fetchAnalysis = useCallback(
    async (forceRefresh = false) => {
      if (!school || !gradeNumber || !section) {
        return;
      }

      if (!isMountedRef.current) {
        return;
      }

      setAnalysisError(null);
      
      // Show immediate feedback - set loading flag but don't change status yet
      // Backend will tell us the actual status (could be 'ready' if hash unchanged, or 'queued' if job created)
      if (forceRefresh) {
        setIsRefreshing(true);
      }

      try {
        const data = await analyzeClassConversations(school, gradeNumber, section, forceRefresh);

        if (!isMountedRef.current) {
          return;
        }

        if (data.analysis !== undefined) {
          setAnalysis(data.analysis ?? null);
        }
        setComputedAt(data.computed_at ?? null);

        const shouldPoll = Boolean(data.job_id && (data.status === 'queued' || data.status === 'running'));
        const nextStatus: AnalysisStatus =
          data.status === 'failed'
            ? 'failed'
            : shouldPoll
            ? data.status
            : 'ready';

        setAnalysisStatus(nextStatus);
        setIsRefreshing(false);
        
        if (shouldPoll) {
          const job = data.job_id as string;
          setJobId(job);
          stopPolling();
          pollJob(job);
        } else {
          setJobId(null);
          stopPolling();
        }
        
        if (nextStatus === 'failed') {
          setAnalysisError('Analysis failed. Please try again.');
        }
      } catch (err) {
        console.error('Failed to analyze class conversations:', err);
        if (!isMountedRef.current) {
          return;
        }

        setIsRefreshing(false);
        
        // On timeout (503/504), the job is likely running in the background
        if (isTimeoutError(err)) {
          setAnalysisStatus('running');
          setAnalysisError('Analysis is being prepared. Please come back in a couple of minutes and refresh the page.');
          return;
        }

        // Real error
        setAnalysisStatus('failed');
        setJobId(null);
        setAnalysisError(err instanceof Error ? err.message : 'Failed to generate analysis. Please try again.');
        stopPolling();
      }
    },
    [school, gradeNumber, section, pollJob, stopPolling]
  );

  // Trigger analysis whenever class identifiers change
  useEffect(() => {
    if (!school || !gradeNumber || !section) {
      return;
    }

    fetchAnalysis();
  }, [school, gradeNumber, section, fetchAnalysis]);

  // Flatten the latest conversations with student info
  const conversations: ConversationWithStudent[] = useMemo(() => {
    if (!students) return [];
    
    return students
      .filter(({ latest_conversation }) => latest_conversation !== null && latest_conversation !== undefined)
      .map(({ student, latest_conversation }) => ({
        ...latest_conversation!,
        student_id: student.id,
        student_name: student.first_name,
        student_roll_number: student.roll_number,
      }))
      .sort((a, b) => 
        new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
      );
  }, [students]);

  const summaryChips = [
    { label: 'School', value: school, icon: '🏫' },
    { label: 'Grade', value: gradeNumber ? `Grade ${gradeNumber}` : undefined, icon: '📘' },
    { label: 'Section', value: section ? `Section ${section}` : undefined, icon: '✏️' },
  ].filter((chip) => Boolean(chip.value));

  return (
    <div className="min-h-screen bg-slate-50 py-12 px-4">
      <div className="mx-auto w-full max-w-4xl">
        <div className="rounded-3xl bg-white px-6 py-10 shadow-2xl shadow-slate-200 sm:px-10 space-y-10">
          <section className="text-center space-y-6">
            <div className="space-y-3">
              <h1 className="text-4xl font-semibold text-slate-900">Class Summary</h1>
              <div className="mx-auto h-1 w-20 rounded-full bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500" />
            </div>
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
          </section>

          <section className="space-y-6">
            {isLoading && <p className="text-sm text-slate-500">Loading conversations...</p>}
            {error && <p className="text-sm text-red-600">{error}</p>}

            {!isLoading && !error && (
              <>
                {conversations.length === 0 ? (
                  <p className="text-sm text-slate-500">No conversations found for this class.</p>
                ) : (
                  <>
                    {showAnalysisLoading && (
                      <AnalysisLoading 
                        key="analysis-loading" 
                        message={analysisStatus === 'queued' ? 'Analysis queued...' : 'Generating analysis...'}
                        subtext="This typically takes 1-2 minutes. You can wait or come back later."
                      />
                    )}
                    {analysisError && (
                      <div className={`rounded-lg p-4 ${analysisError.includes('longer than expected') ? 'bg-amber-50' : 'bg-red-50'}`}>
                        <p className={`text-sm ${analysisError.includes('longer than expected') ? 'text-amber-700' : 'text-red-700'}`}>
                          {analysisError}
                        </p>
                      </div>
                    )}
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <h2 className="text-2xl font-semibold text-slate-900">Class Analysis</h2>
                        {computedAt && (
                          <p className="text-xs text-slate-500">
                            Last updated {new Date(computedAt).toLocaleString()}
                          </p>
                        )}
                        {(isRefreshing || (analysis && jobId && (analysisStatus === 'queued' || analysisStatus === 'running'))) && (
                          <p className="text-xs text-indigo-600 font-medium">Refreshing analysis…</p>
                        )}
                      </div>
                      <button
                        type="button"
                        onClick={() => fetchAnalysis(true)}
                        className="inline-flex items-center justify-center rounded-full bg-slate-900 px-4 py-2 text-xs font-semibold text-white shadow transition hover:bg-slate-800 disabled:opacity-60 disabled:cursor-not-allowed"
                        disabled={isRefreshing || (isAnalysisInProgress && !analysis)}
                      >
                        {isRefreshing ? 'Refreshing...' : 'Refresh Analysis'}
                      </button>
                    </div>
                    {analysis && (
                      <div className="space-y-4">
                        <div className="rounded-lg bg-slate-50 p-6">
                          <div className="text-slate-700 leading-relaxed">
                            {parse(analysis)}
                          </div>
                        </div>
                      </div>
                    )}
                    {!analysis && !analysisError && analysisStatus === 'ready' && (
                      <div className="rounded-lg bg-yellow-50 p-4">
                        <p className="text-sm text-yellow-700">Analysis completed but no content received.</p>
                      </div>
                    )}
                  </>
                )}
              </>
            )}
          </section>

          <button
            onClick={() => navigate('/class-details', { state: { school, grade, section } })}
            className="inline-flex w-full items-center justify-center rounded-full bg-indigo-600 px-6 py-3 text-sm font-semibold text-white shadow-lg shadow-indigo-200/60 transition hover:bg-indigo-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-indigo-500"
          >
            Back to Class Details
          </button>
        </div>
      </div>
    </div>
  );
};

export default ClassSummary;
