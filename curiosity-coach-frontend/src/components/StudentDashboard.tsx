import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { getProjectSources, subscribeToProject } from '../services/api';
import { ProjectSource } from '../types';

const StudentDashboard: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();

  const [sources, setSources] = useState<ProjectSource[]>([]);
  const [selectedSourceId, setSelectedSourceId] = useState<number | ''>('');
  const [loadingSources, setLoadingSources] = useState(false);
  const [isSubscribing, setIsSubscribing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const studentName = useMemo(
    () => user?.student?.first_name || user?.name || 'Student',
    [user]
  );

  useEffect(() => {
    let isMounted = true;
    const loadSources = async () => {
      setLoadingSources(true);
      setError(null);
      try {
        const projectSources = await getProjectSources();
        if (!isMounted) {
          return;
        }
        setSources(projectSources);
        if (projectSources.length > 0) {
          setSelectedSourceId(projectSources[0].id);
        }
      } catch (err: any) {
        if (!isMounted) {
          return;
        }
        setError(err.message || 'Failed to load project list');
      } finally {
        if (isMounted) {
          setLoadingSources(false);
        }
      }
    };

    loadSources();
    return () => {
      isMounted = false;
    };
  }, []);

  const handleSubscribe = async () => {
    if (selectedSourceId === '') {
      setError('Please select a project');
      return;
    }

    setIsSubscribing(true);
    setError(null);
    setSuccess(null);
    try {
      const result = await subscribeToProject(selectedSourceId);
      setSuccess(
        `Subscribed successfully. ${result.created_count} new rows created, ${result.existing_count} already existed.`
      );
    } catch (err: any) {
      setError(err.message || 'Failed to subscribe to project');
    } finally {
      setIsSubscribing(false);
    }
  };

  return (
    <div className="main-gradient-bg min-h-screen px-4 py-8 sm:px-6 lg:px-8">
      <div className="mx-auto w-full max-w-4xl space-y-6">
        <div className="rounded-2xl border border-violet-200 bg-white/95 p-6 shadow-sm">
          <h1 className="text-2xl font-bold text-slate-900">Hi {studentName}</h1>
          <p className="mt-2 text-slate-600">Welcome back. Choose what you want to work on today.</p>
        </div>

        <div className="rounded-2xl border border-violet-200 bg-white/95 p-6 shadow-sm">
          <h2 className="text-xl font-semibold text-slate-900">Subscribe to a project</h2>
          <p className="mt-1 text-sm text-slate-600">
            Select a project file and we will create your progress rows to begin.
          </p>

          <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center">
            <select
              className="w-full rounded-xl border border-violet-200 bg-white px-3 py-3 text-sm text-slate-900 focus:border-violet-400 focus:outline-none focus:ring-2 focus:ring-violet-200 sm:flex-1 sm:py-2"
              value={selectedSourceId}
              onChange={(e) => setSelectedSourceId(e.target.value ? Number(e.target.value) : '')}
              disabled={loadingSources || sources.length === 0}
            >
              {sources.length === 0 ? (
                <option value="">No projects available</option>
              ) : (
                sources.map((source) => (
                  <option key={source.id} value={source.id}>
                    {source.file_name}
                  </option>
                ))
              )}
            </select>

            <button
              type="button"
              onClick={handleSubscribe}
              disabled={isSubscribing || loadingSources || selectedSourceId === '' || sources.length === 0}
              className="rounded-xl bg-violet-500 px-5 py-3 text-sm font-medium text-white hover:bg-violet-600 focus:outline-none focus:ring-2 focus:ring-violet-200 disabled:cursor-not-allowed disabled:opacity-60 sm:py-2"
            >
              {isSubscribing ? 'Subscribing...' : 'Subscribe'}
            </button>
          </div>

          {error && <div className="mt-3 rounded-xl bg-red-50 px-3 py-2 text-sm text-red-600">{error}</div>}
          {success && <div className="mt-3 rounded-xl bg-green-50 px-3 py-2 text-sm text-green-700">{success}</div>}
        </div>

        <div className="rounded-2xl border border-violet-200 bg-white/95 p-6 shadow-sm">
          <h2 className="text-xl font-semibold text-slate-900">Talk to Curiosity Coach</h2>
          <p className="mt-1 text-sm text-slate-600">
            Start your chat whenever you are ready.
          </p>
          <button
            type="button"
            onClick={() => navigate('/chat')}
            className="mt-4 rounded-xl bg-slate-900 px-5 py-3 text-sm font-medium text-white hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-slate-300 sm:py-2"
          >
            Go to chat
          </button>
        </div>
      </div>
    </div>
  );
};

export default StudentDashboard;
