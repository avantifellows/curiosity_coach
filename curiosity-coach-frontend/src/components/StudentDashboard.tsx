import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AutoAwesomeRounded, Logout } from '@mui/icons-material';
import { useAuth } from '../context/AuthContext';
import { getProjectSources, getSubscribedProjects, subscribeToProject } from '../services/api';
import { ProjectSource, SubscribedProject } from '../types';

const glassPanel =
  'rounded-[1.75rem] border border-white/70 bg-white/45 shadow-[0_8px_40px_-12px_rgba(99,102,241,0.18)] backdrop-blur-xl';

const StudentDashboard: React.FC = () => {
  const navigate = useNavigate();
  const { user, logout } = useAuth();

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

  const initials = useMemo(() => {
    const parts = studentName.trim().split(/\s+/);
    if (parts.length >= 2) {
      return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
    }
    return studentName.slice(0, 2).toUpperCase() || 'S';
  }, [studentName]);

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
      if (result.created_count > 0) {
        setSuccess("You're set for this project. Open the coach when you're ready to chat.");
      } else {
        setSuccess('You already had access to this project. Pick it in chat anytime.');
      }
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
    <div className="relative min-h-screen overflow-x-hidden bg-gradient-to-b from-[#f3efff] via-white to-[#eefaf6] font-sans text-slate-900">
      {/* Mesh-style accents */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden" aria-hidden>
        <div className="absolute -top-32 right-[-10%] h-[28rem] w-[28rem] rounded-full bg-violet-400/25 blur-3xl" />
        <div className="absolute top-[40%] left-[-15%] h-[22rem] w-[22rem] rounded-full bg-emerald-300/20 blur-3xl" />
        <div className="absolute bottom-[-10%] right-[20%] h-64 w-64 rounded-full bg-fuchsia-300/15 blur-3xl" />
      </div>

      <header className="fixed top-0 left-0 right-0 z-40 border-b border-white/60 bg-white/50 backdrop-blur-xl supports-[backdrop-filter]:bg-white/40">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:h-[4.25rem] sm:px-6">
          <div className="flex min-w-0 items-center gap-2.5">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-violet-500 to-indigo-600 text-white shadow-md shadow-violet-500/30">
              <AutoAwesomeRounded sx={{ fontSize: 20 }} />
            </span>
            <span className="truncate text-base font-semibold tracking-tight text-slate-900 sm:text-lg">
              Curiosity Coach
            </span>
          </div>
          <div className="flex items-center gap-3">
            <span
              className="hidden h-9 w-9 shrink-0 items-center justify-center rounded-full border border-white/80 bg-white/60 text-xs font-semibold text-violet-700 shadow-sm sm:flex"
              title={studentName}
            >
              {initials}
            </span>
            <button
              type="button"
              onClick={logout}
              className="flex items-center gap-1 rounded-full px-3 py-2 text-sm font-medium text-slate-600 transition-colors hover:bg-white/60 hover:text-slate-900"
            >
              <Logout sx={{ fontSize: 18 }} />
              <span className="hidden sm:inline">Log out</span>
            </button>
          </div>
        </div>
      </header>

      <main className="relative z-10 mx-auto max-w-6xl px-4 pb-16 pt-24 sm:px-6 sm:pt-28">
        <div className="grid grid-cols-1 gap-4 sm:gap-5 lg:grid-cols-12 lg:gap-5">
          {/* Hero */}
          <section className={`${glassPanel} p-6 sm:p-8 lg:col-span-8`}>
            <p className="text-sm font-medium uppercase tracking-widest text-violet-600/90">Your space</p>
            <h1 className="mt-3 text-4xl font-semibold leading-[1.1] tracking-tight text-slate-900 sm:text-5xl">
              Welcome back,{' '}
              <span className="bg-gradient-to-r from-violet-600 via-violet-500 to-fuchsia-500 bg-clip-text text-transparent">
                {studentName}
              </span>
            </h1>
            <p className="mt-4 max-w-xl text-base leading-relaxed text-slate-600 sm:text-lg">
              Pick a project to unlock your chapter path, then open the coach for a focused conversation.
            </p>
          </section>

          {/* Primary CTA — coach */}
          <section className={`${glassPanel} flex flex-col justify-between p-6 sm:p-7 lg:col-span-4`}>
            <div>
              <p className="text-sm font-medium text-slate-500">Next step</p>
              <h2 className="mt-2 text-xl font-semibold tracking-tight text-slate-900">Curiosity Coach</h2>
              <p className="mt-2 text-sm leading-relaxed text-slate-600">
                Continue where you left off or start a new chapter chat.
              </p>
            </div>
            <button
              type="button"
              onClick={openChatPicker}
              className="mt-6 w-full rounded-full bg-gradient-to-r from-violet-600 to-indigo-600 px-6 py-3.5 text-sm font-semibold text-white shadow-lg shadow-violet-500/25 transition hover:from-violet-500 hover:to-indigo-500 hover:shadow-violet-500/35 focus:outline-none focus:ring-2 focus:ring-violet-400 focus:ring-offset-2 focus:ring-offset-transparent"
            >
              Open Curiosity Coach
            </button>
          </section>

          {/* Subscribe — wide */}
          <section className={`${glassPanel} p-6 sm:p-8 lg:col-span-7`}>
            <div className="flex flex-wrap items-end justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold tracking-tight text-slate-900 sm:text-xl">Projects</h2>
                <p className="mt-1 text-sm text-slate-600">
                  Subscribe once per file to track your progress across chapters.
                </p>
              </div>
            </div>

            <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:items-stretch">
              <div className="relative min-h-[3rem] flex-1">
                <select
                  className="h-full w-full cursor-pointer appearance-none rounded-2xl border border-slate-200/80 bg-white/70 py-3 pl-4 pr-10 text-sm font-medium text-slate-900 shadow-inner shadow-slate-900/5 backdrop-blur-sm transition focus:border-violet-400 focus:outline-none focus:ring-2 focus:ring-violet-200/80 disabled:cursor-not-allowed disabled:opacity-50"
                  value={selectedSourceId}
                  onChange={(e) => setSelectedSourceId(e.target.value ? Number(e.target.value) : '')}
                  disabled={loadingSources || sources.length === 0}
                  aria-label="Choose project file"
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
                <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-slate-400">▾</span>
              </div>
              <button
                type="button"
                onClick={handleSubscribe}
                disabled={isSubscribing || loadingSources || selectedSourceId === '' || sources.length === 0}
                className="shrink-0 rounded-2xl border-2 border-violet-400/70 bg-white/50 px-6 py-3 text-sm font-semibold text-violet-700 backdrop-blur-sm transition hover:border-violet-500 hover:bg-violet-50/80 focus:outline-none focus:ring-2 focus:ring-violet-300 disabled:cursor-not-allowed disabled:opacity-50 sm:min-w-[8.5rem]"
              >
                {isSubscribing ? 'Working…' : 'Subscribe'}
              </button>
            </div>

            {error && (
              <div className="mt-4 rounded-2xl border border-red-200/80 bg-red-50/90 px-4 py-3 text-sm text-red-700 backdrop-blur-sm">
                {error}
              </div>
            )}
            {success && (
              <div className="mt-4 rounded-2xl border border-emerald-200/80 bg-emerald-50/90 px-4 py-3 text-sm text-emerald-800 backdrop-blur-sm">
                {success}
              </div>
            )}
          </section>

          {/* Side hint card */}
          <section className={`${glassPanel} flex flex-col justify-center p-6 sm:p-7 lg:col-span-5`}>
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Tip</p>
            <p className="mt-2 text-sm leading-relaxed text-slate-600">
              After you subscribe, use <span className="font-medium text-slate-800">Open Curiosity Coach</span> and
              choose which project this session is for—or try random if you want variety.
            </p>
          </section>
        </div>
      </main>

      {isChatModalOpen && (
        <div
          className="mobile-modal fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4 backdrop-blur-sm"
          role="dialog"
          aria-modal="true"
          aria-labelledby="chat-picker-title"
        >
          <div className="w-full max-w-md rounded-[1.75rem] border border-white/60 bg-white/85 p-6 shadow-2xl shadow-violet-900/10 backdrop-blur-2xl sm:p-8">
            <h3 id="chat-picker-title" className="text-xl font-semibold tracking-tight text-slate-900">
              Choose a project
            </h3>
            <p className="mt-2 text-sm leading-relaxed text-slate-600">
              This session will use the chapter and units from the project you pick.
            </p>

            <div className="mt-5 max-h-[min(50vh,20rem)] space-y-2 overflow-y-auto custom-scrollbar pr-1">
              {loadingSubscribedProjects && (
                <div className="rounded-2xl border border-slate-200/80 bg-white/60 px-4 py-3 text-sm text-slate-600">
                  Loading your projects…
                </div>
              )}

              {!loadingSubscribedProjects && subscribedProjects.length === 0 && (
                <div className="rounded-2xl border border-amber-200/80 bg-amber-50/90 px-4 py-3 text-sm text-amber-900">
                  Subscribe to a project first, then come back to start a chat.
                </div>
              )}

              {!loadingSubscribedProjects && subscribedProjects.length > 0 && (
                <>
                  {subscribedProjects.map((project) => (
                    <label
                      key={project.kb_source_id}
                      className={`flex cursor-pointer items-center gap-3 rounded-2xl border px-4 py-3 text-sm transition ${
                        selectedChatOption === String(project.kb_source_id)
                          ? 'border-violet-400 bg-violet-50/80 text-slate-900 ring-1 ring-violet-300/60'
                          : 'border-slate-200/80 bg-white/50 text-slate-800 hover:border-violet-200 hover:bg-white/80'
                      }`}
                    >
                      <input
                        type="radio"
                        name="chat-project-option"
                        value={String(project.kb_source_id)}
                        checked={selectedChatOption === String(project.kb_source_id)}
                        onChange={(e) => setSelectedChatOption(e.target.value)}
                        className="h-4 w-4 accent-violet-600"
                      />
                      <span className="font-medium">{project.file_name}</span>
                    </label>
                  ))}

                  <label
                    className={`flex cursor-pointer items-center gap-3 rounded-2xl border px-4 py-3 text-sm font-medium transition ${
                      selectedChatOption === 'random'
                        ? 'border-violet-400 bg-violet-50/80 text-slate-900 ring-1 ring-violet-300/60'
                        : 'border-slate-200/80 bg-white/50 text-slate-800 hover:border-violet-200 hover:bg-white/80'
                    }`}
                  >
                    <input
                      type="radio"
                      name="chat-project-option"
                      value="random"
                      checked={selectedChatOption === 'random'}
                      onChange={(e) => setSelectedChatOption(e.target.value)}
                      className="h-4 w-4 accent-violet-600"
                    />
                    <span>Random project</span>
                  </label>
                </>
              )}

              {chatPickerError && (
                <div className="rounded-2xl border border-red-200/80 bg-red-50/90 px-4 py-3 text-sm text-red-700">
                  {chatPickerError}
                </div>
              )}
            </div>

            <div className="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
              <button
                type="button"
                onClick={closeChatPicker}
                className="rounded-full border border-slate-200 bg-white/70 px-5 py-2.5 text-sm font-medium text-slate-700 backdrop-blur-sm transition hover:bg-white"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleContinueToChat}
                disabled={loadingSubscribedProjects || subscribedProjects.length === 0 || !selectedChatOption}
                className="rounded-full bg-gradient-to-r from-violet-600 to-indigo-600 px-5 py-2.5 text-sm font-semibold text-white shadow-md shadow-violet-500/20 transition hover:from-violet-500 hover:to-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
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
