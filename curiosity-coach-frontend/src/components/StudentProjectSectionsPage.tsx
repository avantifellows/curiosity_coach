import React, { useEffect, useMemo, useState } from 'react';
import { Link, useLocation, useParams } from 'react-router-dom';
import { ArrowBack, AutoAwesome, MenuBook } from '@mui/icons-material';
import { getProjectSections } from '../services/api';
import { ProjectSection } from '../types';

type LocationState = { fileName?: string } | null;

const StudentProjectSectionsPage: React.FC = () => {
  const { kbSourceId: rawId } = useParams<{ kbSourceId: string }>();
  const location = useLocation();
  const kbSourceId = Number(rawId);
  const projectTitle =
    (location.state as LocationState)?.fileName?.trim() || 'Your project';

  const [sections, setSections] = useState<ProjectSection[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [selectedPk, setSelectedPk] = useState<number | null>(null);

  useEffect(() => {
    if (!Number.isFinite(kbSourceId) || kbSourceId < 1) {
      setErr('Invalid project link.');
      setLoading(false);
      return;
    }
    let alive = true;
    (async () => {
      setLoading(true);
      setErr(null);
      try {
        const list = await getProjectSections(kbSourceId);
        if (!alive) return;
        setSections(list);
        if (list.length > 0) {
          setSelectedPk(list[0].id);
        } else {
          setSelectedPk(null);
        }
      } catch (e: any) {
        if (!alive) return;
        setErr(e.message || 'Could not load sections');
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, [kbSourceId]);

  const selected = useMemo(
    () => sections.find((s) => s.id === selectedPk) ?? null,
    [sections, selectedPk]
  );

  const openChat = () => {
    if (!selectedPk) return;
    const params = new URLSearchParams({
      project_source_id: String(kbSourceId),
      section_id: String(selectedPk),
      project_selection: 'selected',
    });
    window.open(`/chat?${params.toString()}`, '_blank', 'noopener,noreferrer');
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-slate-800/80 bg-slate-900/80 px-4 py-4 backdrop-blur sm:px-6">
        <div className="mx-auto flex max-w-6xl items-center gap-4">
          <Link
            to="/student-dashboard"
            className="inline-flex items-center gap-1.5 rounded-full border border-slate-700 bg-slate-800/60 px-3 py-2 text-sm font-medium text-slate-200 transition hover:border-slate-500 hover:bg-slate-800"
          >
            <ArrowBack sx={{ fontSize: 18 }} />
            <span className="hidden sm:inline">Dashboard</span>
          </Link>
          <div className="min-w-0 flex-1">
            <h1 className="truncate text-lg font-semibold tracking-tight text-white sm:text-xl">
              {projectTitle}
            </h1>
            <p className="truncate text-xs text-slate-400 sm:text-sm">Choose a section, then open the coach</p>
          </div>
        </div>
      </header>

      <div className="mx-auto flex max-w-6xl min-h-[calc(100vh-5rem)] flex-col lg:flex-row">
        <aside className="border-b border-slate-800 lg:w-80 lg:shrink-0 lg:border-b-0 lg:border-r lg:py-6">
          <div className="p-4 lg:sticky lg:top-4 lg:max-h-[calc(100vh-6rem)] lg:overflow-y-auto lg:px-4">
            <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">Sections</p>
            {loading && (
              <div className="space-y-2">
                {[1, 2, 3, 4].map((k) => (
                  <div
                    key={k}
                    className="h-14 animate-pulse rounded-xl bg-slate-800/80"
                  />
                ))}
              </div>
            )}
            {!loading && err && (
              <div className="rounded-xl border border-amber-900/60 bg-amber-950/40 px-3 py-2 text-sm text-amber-100">
                {err}
              </div>
            )}
            {!loading && !err && sections.length === 0 && (
              <p className="text-sm text-slate-400">No sections for this project yet.</p>
            )}
            {!loading && !err && sections.length > 0 && (
              <ul className="flex gap-2 overflow-x-auto pb-1 lg:flex-col lg:gap-2 lg:overflow-visible lg:pb-0">
                {sections.map((s, idx) => {
                  const active = s.id === selectedPk;
                  return (
                    <li key={s.id} className="shrink-0 lg:shrink">
                      <button
                        type="button"
                        onClick={() => setSelectedPk(s.id)}
                        className={`flex w-64 flex-col rounded-xl border px-3 py-2.5 text-left transition lg:w-full ${
                          active
                            ? 'border-white bg-white text-slate-900 shadow-lg shadow-black/20'
                            : 'border-slate-700/80 bg-slate-900/40 text-slate-100 hover:border-slate-500 hover:bg-slate-800/80'
                        }`}
                      >
                        <span className="text-xs font-medium text-slate-500 line-clamp-1 lg:text-[0.65rem]">
                          {active ? 'Selected' : `Section ${idx + 1}`}
                        </span>
                        <span className="mt-0.5 line-clamp-2 text-sm font-semibold leading-snug">
                          {s.section_name || s.curriculum_section_key || 'Section'}
                        </span>
                        <span
                          className={`mt-1 text-xs ${
                            active ? 'text-slate-600' : 'text-slate-500'
                          }`}
                        >
                          Curiosity Coach chat
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </aside>

        <main className="flex flex-1 flex-col bg-gradient-to-b from-slate-900 to-slate-950 px-4 py-8 sm:px-8">
          {selected && (
            <>
              <div className="mb-6 flex items-start gap-3">
                <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-violet-500/20 text-violet-300 ring-1 ring-violet-500/30">
                  <MenuBook sx={{ fontSize: 26 }} />
                </span>
                <div className="min-w-0">
                  <p className="text-xs font-medium uppercase tracking-wider text-violet-300/90">
                    Curiosity Coach
                  </p>
                  <h2 className="mt-1 text-2xl font-semibold tracking-tight text-white sm:text-3xl">
                    {selected.section_name || 'Section'}
                  </h2>
                  {selected.description_preview ? (
                    <p className="mt-3 max-w-2xl text-sm leading-relaxed text-slate-400 sm:text-base">
                      {selected.description_preview}
                    </p>
                  ) : null}
                </div>
              </div>

              <div className="mt-auto flex flex-1 flex-col items-center justify-center pb-12 pt-4">
                <div className="w-full max-w-md rounded-2xl border border-slate-700/80 bg-slate-900/60 p-6 text-center shadow-xl shadow-black/30 backdrop-blur-sm sm:p-8">
                  <AutoAwesome className="mx-auto text-violet-400" sx={{ fontSize: 36 }} />
                  <p className="mt-4 text-base font-medium text-slate-200">
                    Ready when you are
                  </p>
                  <p className="mt-2 text-sm text-slate-500">
                    Open a focused conversation for this section.
                  </p>
                  <button
                    type="button"
                    onClick={openChat}
                    className="mt-6 w-full rounded-full bg-gradient-to-r from-violet-500 to-indigo-500 px-6 py-3.5 text-sm font-semibold text-white shadow-lg shadow-violet-900/40 transition hover:from-violet-400 hover:to-indigo-400 focus:outline-none focus:ring-2 focus:ring-violet-400 focus:ring-offset-2 focus:ring-offset-slate-900 disabled:cursor-not-allowed disabled:opacity-40"
                    disabled={!selectedPk}
                  >
                    Talk to Curiosity Coach
                  </button>
                </div>
              </div>
            </>
          )}
          {!loading && !err && sections.length > 0 && !selected && (
            <p className="text-slate-400">Select a section from the list.</p>
          )}
        </main>
      </div>
    </div>
  );
};

export default StudentProjectSectionsPage;
