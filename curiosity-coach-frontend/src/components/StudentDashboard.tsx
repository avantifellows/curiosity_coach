import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { getProjectSources, getSubscribedProjects, subscribeToProject } from '../services/api';
import { ProjectSource, SubscribedProject } from '../types';

const StudentDashboard: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();

  const [sources, setSources] = useState<ProjectSource[]>([]);
  const [selectedSourceId, setSelectedSourceId] = useState<number | ''>('');
  const [loadingSources, setLoadingSources] = useState(false);
  const [isSubscribing, setIsSubscribing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [isChatModalOpen, setIsChatModalOpen] = useState(false);
  const [loadingSubscribedProjects, setLoadingSubscribedProjects] = useState(false);
  const [subscribedProjects, setSubscribedProjects] = useState<SubscribedProject[]>([]);
  const [chatPickerError, setChatPickerError] = useState<string | null>(null);
  const [selectedChatOption, setSelectedChatOption] = useState<string>('');

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

  const openChatPicker = async () => {
    setIsChatModalOpen(true);
    setChatPickerError(null);
    setLoadingSubscribedProjects(true);
    try {
      const projects = await getSubscribedProjects();
      setSubscribedProjects(projects);
      if (projects.length > 0) {
        setSelectedChatOption(String(projects[0].kb_source_id));
      } else {
        setSelectedChatOption('');
      }
    } catch (err: any) {
      setSubscribedProjects([]);
      setSelectedChatOption('');
      setChatPickerError(err.message || 'Failed to load subscribed projects');
    } finally {
      setLoadingSubscribedProjects(false);
    }
  };

  const closeChatPicker = () => {
    setIsChatModalOpen(false);
    setChatPickerError(null);
  };

  const handleContinueToChat = () => {
    if (subscribedProjects.length === 0) {
      return;
    }

    let chosenProject: SubscribedProject | undefined;
    let selectionMode: 'selected' | 'random' = 'selected';

    if (selectedChatOption === 'random') {
      selectionMode = 'random';
      const randomIndex = Math.floor(Math.random() * subscribedProjects.length);
      chosenProject = subscribedProjects[randomIndex];
    } else {
      const selectedId = Number(selectedChatOption);
      chosenProject = subscribedProjects.find((project) => project.kb_source_id === selectedId);
    }

    if (!chosenProject) {
      setChatPickerError('Please choose a valid project option');
      return;
    }

    const params = new URLSearchParams({
      project_source_id: String(chosenProject.kb_source_id),
      project_selection: selectionMode,
    });
    closeChatPicker();
    navigate(`/chat?${params.toString()}`);
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
            onClick={openChatPicker}
            className="mt-4 rounded-xl bg-slate-900 px-5 py-3 text-sm font-medium text-white hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-slate-300 sm:py-2"
          >
            Go to chat
          </button>
        </div>
      </div>

      {isChatModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 px-4">
          <div className="w-full max-w-md rounded-2xl border border-violet-200 bg-white p-6 shadow-lg">
            <h3 className="text-lg font-semibold text-slate-900">Choose project for this chat</h3>
            <p className="mt-1 text-sm text-slate-600">
              Pick one of your subscribed projects or choose random.
            </p>

            <div className="mt-4 space-y-2">
              {loadingSubscribedProjects && (
                <div className="rounded-lg bg-slate-50 px-3 py-2 text-sm text-slate-600">
                  Loading subscribed projects...
                </div>
              )}

              {!loadingSubscribedProjects && subscribedProjects.length === 0 && (
                <div className="rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-700">
                  You have not subscribed to any project yet. Subscribe first, then continue to chat.
                </div>
              )}

              {!loadingSubscribedProjects && subscribedProjects.length > 0 && (
                <>
                  {subscribedProjects.map((project) => (
                    <label
                      key={project.kb_source_id}
                      className="flex cursor-pointer items-center gap-3 rounded-lg border border-violet-200 px-3 py-2 text-sm text-slate-800"
                    >
                      <input
                        type="radio"
                        name="chat-project-option"
                        value={String(project.kb_source_id)}
                        checked={selectedChatOption === String(project.kb_source_id)}
                        onChange={(e) => setSelectedChatOption(e.target.value)}
                      />
                      <span>{project.file_name}</span>
                    </label>
                  ))}

                  <label className="flex cursor-pointer items-center gap-3 rounded-lg border border-violet-200 px-3 py-2 text-sm font-medium text-slate-800">
                    <input
                      type="radio"
                      name="chat-project-option"
                      value="random"
                      checked={selectedChatOption === 'random'}
                      onChange={(e) => setSelectedChatOption(e.target.value)}
                    />
                    <span>Random</span>
                  </label>
                </>
              )}

              {chatPickerError && (
                <div className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">{chatPickerError}</div>
              )}
            </div>

            <div className="mt-5 flex justify-end gap-2">
              <button
                type="button"
                onClick={closeChatPicker}
                className="rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleContinueToChat}
                disabled={loadingSubscribedProjects || subscribedProjects.length === 0 || !selectedChatOption}
                className="rounded-lg bg-slate-900 px-3 py-2 text-sm text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
              >
                Continue
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default StudentDashboard;
