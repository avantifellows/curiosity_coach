import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AutoAwesomeRounded,
  Logout,
  MenuBook,
  ChevronRight,
  LibraryBooksOutlined,
} from '@mui/icons-material';
import { FormControl, InputLabel, MenuItem, Select } from '@mui/material';
import { useAuth } from '../context/AuthContext';
import { getProjectSources, getSubscribedProjects, subscribeToProject } from '../services/api';
import { ProjectSource, SubscribedProject } from '../types';

const glassHero =
  'rounded-[1.75rem] border border-white/80 bg-gradient-to-br from-white/75 via-white/55 to-violet-50/45 shadow-[0_24px_64px_-18px_rgba(99,102,241,0.38)] backdrop-blur-xl ring-1 ring-violet-200/25';

const glassProjects =
  'rounded-[1.75rem] border border-white/70 bg-white/55 shadow-[0_14px_44px_-14px_rgba(15,23,42,0.12)] backdrop-blur-xl';

const addProjectWell =
  'rounded-2xl bg-slate-50/90 p-5 ring-1 ring-slate-200/50 sm:p-6';

const openInNewTab = (path: string) => {
  window.open(path, '_blank', 'noopener,noreferrer');
};

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
  const [loadingSubscribedForCards, setLoadingSubscribedForCards] = useState(false);
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

  const refreshCatalogAndSubscriptions = useCallback(async () => {
    setLoadingSources(true);
    setLoadingSubscribedForCards(true);
    setError(null);
    try {
      const [projectSources, subscribed] = await Promise.all([
        getProjectSources({ availableOnly: true }),
        getSubscribedProjects(),
      ]);
      setSources(projectSources);
      setSubscribedProjects(subscribed);
      setSelectedSourceId((prev) => {
        if (projectSources.length === 0) {
          return '';
        }
        const stillThere = projectSources.some((s) => s.id === prev);
        if (prev !== '' && stillThere) {
          return prev;
        }
        return projectSources[0].id;
      });
    } catch (err: any) {
      setError(err.message || 'Failed to load projects');
    } finally {
      setLoadingSources(false);
      setLoadingSubscribedForCards(false);
    }
  }, []);

  useEffect(() => {
    let isMounted = true;
    (async () => {
      await refreshCatalogAndSubscriptions();
      if (!isMounted) return;
    })();
    return () => {
      isMounted = false;
    };
  }, [refreshCatalogAndSubscriptions]);

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
      await refreshCatalogAndSubscriptions();
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
        setSelectedChatOption('random');
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
    if (selectedChatOption === 'random') {
      closeChatPicker();
      openInNewTab('/chat');
      return;
    }

    const selectedId = Number(selectedChatOption);
    const chosenProject = subscribedProjects.find((project) => project.kb_source_id === selectedId);

    if (!chosenProject) {
      setChatPickerError('Please choose a valid project option');
      return;
    }

    const params = new URLSearchParams({
      project_source_id: String(chosenProject.kb_source_id),
      project_selection: 'selected',
      pipeline_slot: 'tutor',
      query_mode: 'opening_only',
      debug: 'true',
    });
    closeChatPicker();
    openInNewTab(`/chat?${params.toString()}`);
  };

  return (
    <div className="relative min-h-screen overflow-x-hidden bg-gradient-to-b from-[#f3efff] via-white to-[#eefaf6] font-sans text-slate-900">
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

      <main className="relative z-10 mx-auto max-w-6xl space-y-9 px-4 pb-20 pt-24 sm:space-y-10 sm:px-6 sm:pt-28">
        {/* Welcome — hero emphasis */}
        <section className={`${glassHero} p-6 sm:p-9 lg:p-10`}>
          <div className="flex flex-col gap-8 lg:flex-row lg:items-end lg:justify-between lg:gap-12">
            <div className="min-w-0 max-w-2xl">
              <p className="text-sm font-medium uppercase tracking-widest text-violet-600/90">
                Your space
              </p>
              <h1 className="mt-3 text-4xl font-semibold leading-[1.1] tracking-tight text-slate-900 sm:text-5xl">
                Welcome back,{' '}
                <span className="bg-gradient-to-r from-violet-600 via-violet-500 to-fuchsia-500 bg-clip-text text-transparent">
                  {studentName}
                </span>
              </h1>
              <p className="mt-4 text-base leading-relaxed text-slate-600 sm:text-lg">
                Subscribe to projects below, then open the coach for a chapter-focused conversation.
              </p>
            </div>
            <div className="shrink-0 lg:pb-1">
              <button
                type="button"
                onClick={openChatPicker}
                className="w-full min-w-[14rem] rounded-full bg-gradient-to-r from-violet-600 to-indigo-600 px-8 py-4 text-sm font-semibold text-white shadow-lg shadow-violet-500/30 transition hover:from-violet-500 hover:to-indigo-500 hover:shadow-violet-500/40 focus:outline-none focus:ring-2 focus:ring-violet-400 focus:ring-offset-2 focus:ring-offset-transparent sm:w-auto"
              >
                Open Curiosity Coach
              </button>
            </div>
          </div>
        </section>

        {/* Projects */}
        <section className={`${glassProjects} p-6 sm:p-8 lg:p-9`}>
          <div className="flex flex-wrap items-start gap-3">
            <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-violet-500/10 text-violet-700 ring-1 ring-violet-200/60">
              <MenuBook sx={{ fontSize: 24 }} />
            </span>
            <div className="min-w-0 flex-1">
              <h2 className="text-xl font-semibold tracking-tight text-slate-900 sm:text-2xl">Projects</h2>
              <p className="mt-1 max-w-2xl text-sm leading-relaxed text-slate-600 sm:text-base">
                Your library and the catalog—add anything you have not joined yet.
              </p>
            </div>
          </div>

          <div className="mt-8">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500">Your projects</h3>
            {loadingSubscribedForCards && (
              <ul className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3" aria-hidden>
                {[0, 1, 2].map((key) => (
                  <li
                    key={key}
                    className="h-[5.5rem] animate-pulse rounded-2xl bg-gradient-to-r from-slate-200/60 to-slate-100/40"
                  />
                ))}
              </ul>
            )}
            {!loadingSubscribedForCards && subscribedProjects.length === 0 && (
              <div className="mt-4 flex flex-col items-center justify-center rounded-2xl border border-dashed border-slate-300/80 bg-slate-50/70 px-6 py-12 text-center">
                <LibraryBooksOutlined sx={{ fontSize: 48 }} className="text-violet-400/90" />
                <p className="mt-4 max-w-sm text-base font-medium text-slate-800">No projects yet</p>
                <p className="mt-2 max-w-md text-sm leading-relaxed text-slate-600">
                  When you subscribe to a file from the catalog, it will show up here. Use{' '}
                  <span className="font-medium text-slate-800">Add a project</span> below to get started.
                </p>
              </div>
            )}
            {!loadingSubscribedForCards && subscribedProjects.length > 0 && (
              <ul className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {subscribedProjects.map((project) => (
                  <li key={project.kb_source_id}>
                    <button
                      type="button"
                      className="group flex min-h-[5.5rem] w-full items-center gap-3 rounded-2xl border border-slate-200/90 bg-white/85 px-4 py-3.5 text-left shadow-sm shadow-slate-900/5 transition hover:border-violet-300/90 hover:bg-white hover:shadow-md hover:shadow-violet-500/10 focus:outline-none focus:ring-2 focus:ring-violet-300/80 focus:ring-offset-2 focus:ring-offset-white/50"
                      onClick={() =>
                        navigate(`/projects/${project.kb_source_id}`, {
                          state: { fileName: project.file_name },
                        })
                      }
                    >
                      <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-violet-500/[0.08] text-violet-600 transition group-hover:bg-violet-500/15">
                        <MenuBook sx={{ fontSize: 22 }} />
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="line-clamp-2 text-[0.9375rem] font-semibold leading-snug text-slate-900">
                          {project.file_name}
                        </span>
                      </span>
                      <ChevronRight
                        sx={{ fontSize: 22 }}
                        className="shrink-0 text-slate-300 transition group-hover:translate-x-0.5 group-hover:text-violet-500"
                      />
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className={`${addProjectWell} mt-10`}>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-600">Add a project</h3>
            <p className="mt-1 text-sm text-slate-600">
              Pick a file from the catalog you are not subscribed to yet.
            </p>
            <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-end">
              <FormControl
                fullWidth
                size="small"
                disabled={loadingSources || sources.length === 0}
                sx={{
                  flex: 1,
                  '& .MuiOutlinedInput-root': {
                    borderRadius: '0.875rem',
                    backgroundColor: 'rgba(255,255,255,0.92)',
                  },
                }}
              >
                <InputLabel id="student-dashboard-source-label">Project file</InputLabel>
                <Select
                  labelId="student-dashboard-source-label"
                  id="student-dashboard-source-select"
                  label="Project file"
                  value={selectedSourceId === '' ? '' : String(selectedSourceId)}
                  onChange={(e) => {
                    const v = e.target.value as string;
                    setSelectedSourceId(v === '' ? '' : Number(v));
                  }}
                >
                  {sources.length === 0 ? (
                    <MenuItem value="" disabled>
                      No more projects to add
                    </MenuItem>
                  ) : (
                    sources.map((source) => (
                      <MenuItem key={source.id} value={String(source.id)}>
                        {source.file_name}
                      </MenuItem>
                    ))
                  )}
                </Select>
              </FormControl>
              <button
                type="button"
                onClick={handleSubscribe}
                disabled={
                  isSubscribing || loadingSources || selectedSourceId === '' || sources.length === 0
                }
                className="shrink-0 rounded-xl border border-slate-300/90 bg-white px-6 py-2.5 text-sm font-semibold text-slate-800 shadow-sm transition hover:border-violet-400 hover:bg-violet-50/90 hover:text-violet-900 focus:outline-none focus:ring-2 focus:ring-violet-300 disabled:cursor-not-allowed disabled:opacity-50 sm:min-h-[40px] sm:min-w-[9.5rem]"
              >
                {isSubscribing ? 'Working…' : 'Subscribe'}
              </button>
            </div>
          </div>

          {error && (
            <div className="mt-6 rounded-2xl border border-red-200/80 bg-red-50/90 px-4 py-3 text-sm text-red-700 backdrop-blur-sm">
              {error}
            </div>
          )}
          {success && (
            <div className="mt-6 rounded-2xl border border-emerald-200/80 bg-emerald-50/90 px-4 py-3 text-sm text-emerald-800 backdrop-blur-sm">
              {success}
            </div>
          )}
        </section>
      </main>

      {isChatModalOpen && (
        <div
          className="mobile-modal fixed inset-0 z-50 flex items-center justify-center bg-slate-900/45 p-4 backdrop-blur-sm"
          role="dialog"
          aria-modal="true"
          aria-labelledby="chat-picker-title"
        >
          <div className="w-full max-w-md rounded-[1.75rem] border border-white/70 bg-white/92 p-6 shadow-2xl shadow-violet-900/15 ring-1 ring-slate-200/40 backdrop-blur-2xl sm:p-8">
            <h3 id="chat-picker-title" className="text-xl font-semibold tracking-tight text-slate-900">
              Choose a project
            </h3>
            <p className="mt-2 text-sm leading-relaxed text-slate-600">
              This session will use the chapter and units from the project you pick.
            </p>

            <div className="mt-5 max-h-[min(50vh,20rem)] space-y-2 overflow-y-auto custom-scrollbar pr-1">
              {loadingSubscribedProjects && (
                <div className="rounded-2xl border border-slate-200/80 bg-slate-50/80 px-4 py-3 text-sm text-slate-600">
                  Loading your projects…
                </div>
              )}

              {!loadingSubscribedProjects && subscribedProjects.length === 0 && (
                <label
                  className={`flex cursor-pointer items-center gap-3 rounded-2xl border px-4 py-3.5 text-sm font-medium transition ${
                    selectedChatOption === 'random'
                      ? 'border-violet-400 bg-violet-50/90 text-slate-900 ring-2 ring-violet-200/80'
                      : 'border-slate-200/80 bg-white/70 text-slate-800 hover:border-violet-200 hover:bg-white'
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
                  <span>Fresh conversation</span>
                </label>
              )}

              {!loadingSubscribedProjects && subscribedProjects.length > 0 && (
                <>
                  {subscribedProjects.map((project) => (
                    <label
                      key={project.kb_source_id}
                      className={`flex cursor-pointer items-center gap-3 rounded-2xl border px-4 py-3.5 text-sm transition ${
                        selectedChatOption === String(project.kb_source_id)
                          ? 'border-violet-400 bg-violet-50/90 text-slate-900 ring-2 ring-violet-200/80'
                          : 'border-slate-200/80 bg-white/70 text-slate-800 hover:border-violet-200 hover:bg-white'
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
                    className={`flex cursor-pointer items-center gap-3 rounded-2xl border px-4 py-3.5 text-sm font-medium transition ${
                      selectedChatOption === 'random'
                        ? 'border-violet-400 bg-violet-50/90 text-slate-900 ring-2 ring-violet-200/80'
                        : 'border-slate-200/80 bg-white/70 text-slate-800 hover:border-violet-200 hover:bg-white'
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
                    <span>Fresh conversation</span>
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
                className="rounded-full border border-slate-200 bg-white/90 px-5 py-2.5 text-sm font-medium text-slate-700 shadow-sm transition hover:bg-white"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleContinueToChat}
                disabled={loadingSubscribedProjects || !selectedChatOption}
                className="rounded-full bg-gradient-to-r from-violet-600 to-indigo-600 px-5 py-2.5 text-sm font-semibold text-white shadow-md shadow-violet-500/25 transition hover:from-violet-500 hover:to-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
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
