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
      pipeline_key: 'tutor_flow_v1',
      debug: 'true',
    });
    window.open(`/chat?${params.toString()}`, '_blank', 'noopener,noreferrer');
  };

  return (
    <div className="main-gradient-bg min-h-screen text-slate-900">
      <header className="border-b border-violet-200/80 bg-white/85 px-4 py-4 shadow-sm backdrop-blur sm:px-6">
        <div className="mx-auto flex max-w-6xl items-center gap-4">
          <Link
            to="/student-dashboard"
            className="inline-flex items-center gap-1.5 rounded-full border border-violet-200 bg-white/90 px-3 py-2 text-sm font-medium text-violet-700 transition hover:border-violet-300 hover:bg-violet-50"
          >
            <ArrowBack sx={{ fontSize: 18 }} />
            <span className="hidden sm:inline">Dashboard</span>
          </Link>
          <div className="min-w-0 flex-1">
            <h1 className="truncate text-lg font-semibold tracking-tight text-slate-900 sm:text-xl">
              {projectTitle}
            </h1>
            <p className="truncate text-xs text-violet-700 sm:text-sm">Choose a section, then open the coach</p>
          </div>
        </div>
      </header>

      <div className="mx-auto flex max-w-6xl min-h-[calc(100vh-5rem)] flex-col pb-10 lg:flex-row lg:pb-12">
        <aside className="border-b border-violet-200/70 bg-white/35 backdrop-blur-sm lg:w-80 lg:shrink-0 lg:border-b-0 lg:border-r lg:py-6">
          <div className="custom-scrollbar p-4 lg:sticky lg:top-4 lg:max-h-[calc(100vh-6rem)] lg:overflow-y-auto lg:px-4">
            <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-violet-700">Sections</p>
            {loading && (
              <div className="space-y-2">
                {[1, 2, 3, 4].map((k) => (
                  <div
                    key={k}
                    className="h-14 animate-pulse rounded-xl bg-violet-100/70"
                  />
                ))}
              </div>
            )}
            {!loading && err && (
              <div className="rounded-xl border border-amber-200/80 bg-amber-50/90 px-3 py-2 text-sm text-amber-900">
                {err}
              </div>
            )}
            {!loading && !err && sections.length === 0 && (
              <p className="text-sm text-slate-600">No sections for this project yet.</p>
            )}
            {!loading && !err && sections.length > 0 && (
              <ul className="custom-scrollbar flex gap-2 overflow-x-auto pb-2 lg:flex-col lg:gap-2 lg:overflow-visible lg:pb-0">
                {sections.map((s, idx) => {
                  const active = s.id === selectedPk;
                  return (
                    <li key={s.id} className="shrink-0 lg:shrink">
                      <button
                        type="button"
                        onClick={() => setSelectedPk(s.id)}
                        className={`flex w-64 flex-col rounded-xl border px-3 py-2.5 text-left shadow-sm transition lg:w-full ${
                          active
                            ? 'border-violet-400 bg-violet-50 text-slate-900 ring-2 ring-violet-200/80'
                            : 'border-violet-100/90 bg-white/80 text-slate-800 hover:border-violet-300 hover:bg-white'
                        }`}
                      >
                        <span
                          className={`line-clamp-1 text-xs font-medium lg:text-[0.65rem] ${
                            active ? 'text-violet-700' : 'text-slate-500'
                          }`}
                        >
                          Section {idx + 1}
                        </span>
                        <span className="mt-0.5 line-clamp-2 text-sm font-semibold leading-snug">
                          {s.section_name || s.curriculum_section_key || 'Section'}
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </aside>

        <main className="flex flex-1 flex-col px-4 pb-12 pt-8 sm:px-8 lg:pb-16">
          {selected && (
            <>
              <div className="mb-6 flex items-start gap-3">
                <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-violet-100 text-violet-700 ring-1 ring-violet-200">
                  <MenuBook sx={{ fontSize: 26 }} />
                </span>
                <div className="min-w-0">
                  <p className="text-xs font-medium uppercase tracking-wider text-violet-700">
                    Project section
                  </p>
                  <h2 className="mt-1 text-2xl font-semibold tracking-tight text-slate-900 sm:text-3xl">
                    {selected.section_name || 'Section'}
                  </h2>
                  {selected.description_preview ? (
                    <p className="mt-3 max-w-2xl text-sm leading-relaxed text-slate-600 sm:text-base">
                      {selected.description_preview}
                    </p>
                  ) : null}
                </div>
              </div>

              <div className="mt-auto flex flex-1 flex-col items-center justify-center pb-10 pt-4">
                <div className="w-full max-w-md rounded-2xl border border-violet-200 bg-white/90 p-6 text-center shadow-sm backdrop-blur-sm sm:p-8">
                  <AutoAwesome className="mx-auto text-violet-600" sx={{ fontSize: 36 }} />
                  <p className="mt-4 text-base font-medium text-slate-900">
                    Ready when you are
                  </p>
                  <p className="mt-2 text-sm text-slate-600">
                    Open a focused conversation for this section.
                  </p>
                  <button
                    type="button"
                    onClick={openChat}
                    className="mt-6 w-full rounded-full bg-gradient-to-r from-violet-600 to-indigo-600 px-6 py-3.5 text-sm font-semibold text-white shadow-lg shadow-violet-500/25 transition hover:from-violet-500 hover:to-indigo-500 focus:outline-none focus:ring-2 focus:ring-violet-300 focus:ring-offset-2 focus:ring-offset-white disabled:cursor-not-allowed disabled:opacity-40"
                    disabled={!selectedPk}
                  >
                    Talk to Curiosity Coach
                  </button>
                </div>
              </div>
            </>
          )}
          {!loading && !err && sections.length > 0 && !selected && (
            <p className="text-slate-600">Select a section from the list.</p>
          )}
        </main>
      </div>
    </div>
  );
};

export default StudentProjectSectionsPage;
