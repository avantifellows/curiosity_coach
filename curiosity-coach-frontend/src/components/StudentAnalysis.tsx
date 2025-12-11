import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Student } from '../types';
import { analyzeStudentConversations, getAnalysisJobStatus } from '../services/api';
import { AnalysisStatus } from '../types';
import parse from 'html-react-parser';

// Helper to detect if an error is likely a timeout (API Gateway 30s limit)
const isTimeoutError = (err: unknown): boolean => {
  if (!axios.isAxiosError(err)) return false;
  return err.code === 'ECONNABORTED' || err.response?.status === 504 || !err.response;
};

const normalizeAnalysisMarkup = (raw: string | null): string | null => {
  if (!raw) {
    return raw;
  }

  const trimmed = raw.trim();
  if (!trimmed) {
    return null;
  }

  const containsDocumentTags = /<\/?html[\s>]/i.test(trimmed) || /<\/?body[\s>]/i.test(trimmed);
  if (containsDocumentTags && typeof window !== 'undefined' && 'DOMParser' in window) {
    try {
      const parser = new window.DOMParser();
      const doc = parser.parseFromString(trimmed, 'text/html');
      const bodyHtml = doc.body?.innerHTML?.trim();
      if (bodyHtml) {
        return bodyHtml;
      }
    } catch (err) {
      console.warn('Failed to normalize analysis markup via DOMParser:', err);
    }
  }

  // Fallback: strip html/body tags if present
  return trimmed
    .replace(/<\/?html[^>]*>/gi, '')
    .replace(/<\/?body[^>]*>/gi, '')
    .trim();
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

interface StudentAnalysisState {
  student?: Student;
}

const StudentAnalysis: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const state = (location.state as StudentAnalysisState) || {};
  const student = state.student;

  const [analysis, setAnalysis] = useState<string | null>(null);
  const [analysisStatus, setAnalysisStatus] = useState<AnalysisStatus>('ready');
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [computedAt, setComputedAt] = useState<string | null>(null);

  const isAnalysisInProgress = analysisStatus === 'queued' || analysisStatus === 'running';
  const showAnalysisLoading = isAnalysisInProgress && !analysis;

  const isMountedRef = useRef(true);
  const pollTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const retryTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const retryCountRef = useRef(0);
  const MAX_RETRIES = 2;

  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      if (pollTimeoutRef.current) clearTimeout(pollTimeoutRef.current);
      if (retryTimeoutRef.current) clearTimeout(retryTimeoutRef.current);
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
          setAnalysis(normalizeAnalysisMarkup(data.analysis ?? null));
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
        console.error('Failed to poll student analysis job:', err);
        setAnalysisStatus('failed');
        setAnalysisError(err instanceof Error ? err.message : 'Failed to fetch analysis status.');
        setJobId(null);
        stopPolling();
      }
    },
    [stopPolling]
  );

  const handleBackToConversations = () => {
    if (typeof window !== 'undefined' && window.history.length > 1) {
      navigate(-1);
      return;
    }

    if (student) {
      navigate('/class-conversation', { state: { student } });
    } else {
      navigate('/teacher-view');
    }
  };

  const fetchAnalysis = useCallback(
    async (forceRefresh = false, isRetry = false) => {
      if (!student) {
        return;
      }

      if (!isMountedRef.current) {
        return;
      }

      // Reset retry count on fresh requests (not retries)
      if (!isRetry) {
        retryCountRef.current = 0;
      }

      setAnalysisError(null);
      setAnalysisStatus(forceRefresh ? 'queued' : 'running');

      try {
        const data = await analyzeStudentConversations(student.id, forceRefresh);

        if (!isMountedRef.current) {
          return;
        }

        // Success - reset retry count
        retryCountRef.current = 0;

        if (data.analysis !== undefined) {
          setAnalysis(normalizeAnalysisMarkup(data.analysis ?? null));
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
        console.error('Failed to analyze student conversations:', err);
        if (!isMountedRef.current) {
          return;
        }

        // On timeout, the backend may have already started the job
        // Retry after a short delay to check for active job
        if (isTimeoutError(err) && retryCountRef.current < MAX_RETRIES) {
          retryCountRef.current += 1;
          console.log(`Request timed out, retrying (${retryCountRef.current}/${MAX_RETRIES})...`);
          // Keep status as running, don't show error yet
          retryTimeoutRef.current = setTimeout(() => {
            // Retry without force refresh to pick up any active job
            fetchAnalysis(false, true);
          }, 3000);
          return;
        }

        // Real error or max retries reached
        setAnalysisStatus('failed');
        setJobId(null);
        setAnalysisError(
          isTimeoutError(err)
            ? 'Analysis is taking longer than expected. Please refresh the page in a minute.'
            : (err instanceof Error ? err.message : 'Failed to generate analysis. Please try again.')
        );
        stopPolling();
      }
    },
    [student, pollJob, stopPolling]
  );

  useEffect(() => {
    if (!student) {
      navigate('/teacher-view', { replace: true });
      return;
    }

    fetchAnalysis();
  }, [student, navigate, fetchAnalysis]);


  return (
    <div className="min-h-screen bg-slate-50 py-12 px-4">
      <div className="mx-auto w-full max-w-4xl">
        <div className="rounded-3xl bg-white px-6 py-10 shadow-2xl shadow-slate-200 sm:px-10 space-y-10">
          <section className="text-center space-y-6">
            <div className="space-y-3">
              <h1 className="text-4xl font-semibold text-slate-900">
                {student?.first_name || 'Student'}'s Analysis
              </h1>
              <div className="mx-auto h-1 w-20 rounded-full bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500" />
            </div>
          </section>

          <section className="space-y-6">
            {showAnalysisLoading && (
              <AnalysisLoading 
                key="analysis-loading" 
                message={analysisStatus === 'queued' ? 'Analysis queued...' : 'Generating analysis...'}
                subtext="This typically takes 1-2 minutes. You can wait or come back later."
              />
            )}
            
            {analysisError && (
              <div className={`rounded-lg p-4 ${analysisError.includes('longer than expected') ? 'bg-amber-50' : 'bg-red-50'}`}>
                <p className={`text-sm ${analysisError.includes('longer than expected') ? 'text-amber-700' : 'text-red-600'}`}>
                  {analysisError}
                </p>
              </div>
            )}

            <div className="flex items-start justify-between gap-3">
              <div className="text-left">
                <h2 className="text-2xl font-semibold text-slate-900">Insights</h2>
                {computedAt && (
                  <p className="text-xs text-slate-500">Last updated {new Date(computedAt).toLocaleString()}</p>
                )}
                {analysis && jobId && (analysisStatus === 'queued' || analysisStatus === 'running') && (
                  <p className="text-xs text-indigo-600 font-medium">Refreshing analysis…</p>
                )}
              </div>
              <button
                type="button"
                onClick={() => fetchAnalysis(true)}
                className="inline-flex items-center justify-center rounded-full bg-slate-900 px-4 py-2 text-xs font-semibold text-white shadow transition hover:bg-slate-800 disabled:opacity-60"
                disabled={isAnalysisInProgress && !analysis}
              >
                Refresh Analysis
              </button>
            </div>

            {analysis && (
              <div className="text-slate-700 leading-relaxed">
                {parse(analysis)}
              </div>
            )}

            {!analysis && !analysisError && analysisStatus === 'ready' && (
              <div className="rounded-lg bg-yellow-50 p-4">
                <p className="text-sm text-yellow-700">Analysis completed but no content received.</p>
              </div>
            )}
          </section>

          <button
            onClick={handleBackToConversations}
            className="inline-flex w-full items-center justify-center rounded-full bg-indigo-600 px-6 py-3 text-sm font-semibold text-white shadow-lg shadow-indigo-200/60 transition hover:bg-indigo-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-indigo-500"
          >
            Back to Conversations
          </button>
        </div>
      </div>
    </div>
  );
};

export default StudentAnalysis;
