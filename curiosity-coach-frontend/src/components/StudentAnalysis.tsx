import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Student } from '../types';
import { analyzeStudentConversations, getAnalysisJobStatus } from '../services/api';
import { AnalysisStatus } from '../types';
import parse from 'html-react-parser';

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

// AnalysisLoading component (inline to avoid module resolution issues)
const AnalysisLoading: React.FC<{ message?: string }> = ({ 
  message = "PROCESSING, IT TAKES AROUND 2 MINS......."
}) => {
  return (
    <div className="flex flex-col items-center justify-center py-12 px-4">
      <div className="text-center">
        <p className="text-lg font-medium text-slate-700 animate-pulse">
          {message}
        </p>
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

  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      if (pollTimeoutRef.current) {
        clearTimeout(pollTimeoutRef.current);
      }
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
    async (forceRefresh = false) => {
      if (!student) {
        return;
      }

      if (!isMountedRef.current) {
        return;
      }

      setAnalysisError(null);
      setAnalysisStatus(forceRefresh ? 'queued' : 'running');

      try {
        const data = await analyzeStudentConversations(student.id, forceRefresh);

        if (!isMountedRef.current) {
          return;
        }

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
        setAnalysisStatus('failed');
        setJobId(null);
        setAnalysisError(err instanceof Error ? err.message : 'Failed to generate analysis. Please try again.');
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
              <AnalysisLoading key="analysis-loading" message={`Analysis ${analysisStatus === 'queued' ? 'queued' : 'running'}...`} />
            )}
            
            {analysisError && (
              <div className="rounded-lg bg-red-50 p-4">
                <p className="text-sm text-red-600">{analysisError}</p>
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
