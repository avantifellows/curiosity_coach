import React, { useEffect, useMemo, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  DashboardHourlyBucket,
  DashboardResponse,
  StudentDailySeries,
  StudentDailyRecord,
  Student,
} from '../types';
import {
  getClassDashboardMetrics,
  getStudentDailyMetrics,
  getStudentsForClass,
  refreshClassMetrics,
} from '../services/api';

interface LocationState {
  school: string;
  grade: number;
  section?: string;
}

type StudentMetricKey = 'user_words' | 'user_messages' | 'avg_depth' | 'total_relevant_questions';

const METRIC_OPTIONS: { value: StudentMetricKey; label: string }[] = [
  { value: 'user_words', label: 'Words typed' },
  { value: 'user_messages', label: 'User messages' },
  { value: 'avg_depth', label: 'Avg depth' },
  { value: 'total_relevant_questions', label: 'Relevant questions' },
];

const METRIC_LABEL: Record<StudentMetricKey, string> = {
  user_words: 'Words typed',
  user_messages: 'User messages',
  avg_depth: 'Avg depth',
  total_relevant_questions: 'Relevant questions',
};

const COMPARISON_COLORS = ['#2563eb', '#f97316', '#10b981', '#facc15'];

const formatNumber = (value: number | null | undefined, options?: Intl.NumberFormatOptions) => {
  if (value === null || value === undefined) {
    return '—';
  }
  return new Intl.NumberFormat(undefined, options).format(value);
};

const formatMinutes = (value: number | null | undefined) =>
  formatNumber(value, { minimumFractionDigits: 1, maximumFractionDigits: 1 });

const formatPercent = (value: number | null | undefined) =>
  value === null || value === undefined
    ? '—'
    : `${formatNumber(value, { minimumFractionDigits: 1, maximumFractionDigits: 1 })}%`;

const formatOneDecimal = (value: number | null | undefined) =>
  value === null || value === undefined
    ? '—'
    : formatNumber(value, { minimumFractionDigits: 1, maximumFractionDigits: 1 });

const IST_TIMEZONE = 'Asia/Kolkata';

const formatDayLabel = (isoDate: string) =>
  new Date(isoDate).toLocaleDateString([], { month: 'short', day: 'numeric' });

const formatHourRange = (startIso: string, endIso: string) => {
  const start = new Date(startIso);
  const end = new Date(endIso);
  const startLabel = start.toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
    timeZone: IST_TIMEZONE,
  });
  const endLabel = end.toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
    timeZone: IST_TIMEZONE,
  });
  const dayLabel = start.toLocaleDateString([], {
    month: 'short',
    day: 'numeric',
    timeZone: IST_TIMEZONE,
  });
  return `${dayLabel} · ${startLabel} – ${endLabel}`;
};

const HourlyActivityChart: React.FC<{ buckets: DashboardHourlyBucket[] }> = ({ buckets }) => {
  const height = 240;
  const width = 720;
  const padding = { top: 16, right: 32, bottom: 48, left: 56 };
  const maxValue = buckets.reduce((acc, bucket) => Math.max(acc, bucket.user_message_count), 0);
  const safeMax = maxValue > 0 ? maxValue : 1;
  const xSpan = width - padding.left - padding.right;
  const ySpan = height - padding.top - padding.bottom;
  const maxLabel =
    maxValue > 0
      ? `Max user msgs/hour: ${formatNumber(maxValue)}`
      : 'No user messages recorded in last 24h';

  const points = buckets.map((bucket, index) => {
    const ratio = buckets.length > 1 ? index / (buckets.length - 1) : 0.5;
    const x = padding.left + ratio * xSpan;
    const y = padding.top + (1 - bucket.user_message_count / safeMax) * ySpan;
    return { x, y, bucket };
  });

  const areaPath = points.length
    ? [
        `M ${points[0].x} ${height - padding.bottom}`,
        ...points.map((point) => `L ${point.x} ${point.y}`),
        `L ${points[points.length - 1].x} ${height - padding.bottom}`,
        'Z',
      ].join(' ')
    : '';

  const linePath = points.length
    ? points.map((point, idx) => `${idx === 0 ? 'M' : 'L'} ${point.x} ${point.y}`).join(' ')
    : '';

  const tickSlots = Math.min(6, points.length);
  const tickInterval = tickSlots > 1 ? Math.max(1, Math.floor((points.length - 1) / (tickSlots - 1))) : 1;
  const tickPoints = points.filter((_, idx) => idx % tickInterval === 0 || idx === points.length - 1);

  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
      <svg viewBox={`0 0 ${width} ${height}`} className="block w-full" role="img" aria-label="Hourly user messages">
        <defs>
          <linearGradient id="hourlyArea" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#6366f1" stopOpacity="0.25" />
            <stop offset="100%" stopColor="#6366f1" stopOpacity="0" />
          </linearGradient>
        </defs>
        <rect x="0" y="0" width={width} height={height} fill="#f8fafc" />
        <line
          x1={padding.left}
          y1={height - padding.bottom}
          x2={width - padding.right}
          y2={height - padding.bottom}
          stroke="#cbd5f5"
          strokeWidth={1}
        />
        {tickPoints.map(({ x }) => (
          <line
            key={`grid-${x}`}
            x1={x}
            y1={padding.top}
            x2={x}
            y2={height - padding.bottom}
            stroke="#e2e8f0"
            strokeWidth={1}
            strokeDasharray="4 6"
          />
        ))}
        <text x={padding.left} y={padding.top + 12} fill="#475569" fontSize="12" fontWeight={500}>
          {maxLabel}
        </text>
        <text
          x={padding.left - 8}
          y={height - padding.bottom}
          fill="#94a3b8"
          fontSize="11"
          textAnchor="end"
        >
          0
        </text>
        <text
          x={padding.left - 40}
          y={padding.top + ySpan / 2}
          fill="#94a3b8"
          fontSize="11"
          transform={`rotate(-90 ${padding.left - 40} ${padding.top + ySpan / 2})`}
        >
          User msgs/hour
        </text>
        {points.length > 0 && (
          <>
            <path d={areaPath} fill="url(#hourlyArea)" />
            <path
              d={linePath}
              fill="none"
              stroke="#4f46e5"
              strokeWidth={2.5}
              strokeLinecap="round"
            />
          </>
        )}
        {points.map(({ x, y, bucket }) => {
          const tooltip = [
            formatHourRange(bucket.window_start, bucket.window_end),
            `${bucket.user_message_count} user msgs`,
            `${bucket.ai_message_count} coach msgs`,
            `${bucket.active_users} active students`,
            `${bucket.after_school_user_count} after-school active`,
          ].join('\n');
          return (
            <g key={bucket.window_start}>
              <circle cx={x} cy={y} r={4.5} fill="#312e81" stroke="#e0e7ff" strokeWidth={1.5} />
              <title>{tooltip}</title>
            </g>
          );
        })}
        {tickPoints.map(({ x, bucket }) => (
          <text
            key={`label-${bucket.window_start}`}
            x={x}
            y={height - padding.bottom + 20}
            fill="#475569"
            fontSize="11"
            textAnchor="middle"
          >
            {new Date(bucket.window_start).toLocaleTimeString([], {
              hour: '2-digit',
              timeZone: IST_TIMEZONE,
            })}
          </text>
        ))}
        <text x={padding.left} y={height - 12} fill="#94a3b8" fontSize="11">
          Hour of day (IST)
        </text>
      </svg>
    </div>
  );
};

interface StudentComparisonChartProps {
  data: StudentDailySeries[];
  metric: StudentMetricKey;
}

const StudentComparisonChart: React.FC<StudentComparisonChartProps> = ({ data, metric }) => {
  if (!data.length) {
    return null;
  }

  const padding = { top: 28, right: 24, bottom: 56, left: 52 };
  const chartHeight = 280;
  const studentCount = data.length;

  const daySet = new Set<string>();
  data.forEach((series) => {
    series.records.forEach((record) => {
      daySet.add(record.day);
    });
  });

  const dayLabels = Array.from(daySet).sort();
  if (dayLabels.length === 0) {
    return (
      <div className="rounded-2xl border border-dashed border-slate-200 bg-white p-8 text-center text-sm text-slate-500">
        No daily metrics yet for the selected student{studentCount > 1 ? 's' : ''}.
      </div>
    );
  }

  const valueLookup = data.map((series) => {
    const recordMap = new Map(series.records.map((record) => [record.day, record]));
    return {
      ...series,
      recordMap,
    };
  });

  const maxValue = valueLookup.reduce((outerMax, series) => {
    return dayLabels.reduce((innerMax, day) => {
      const record = series.recordMap.get(day);
      const value = record ? getMetricValue(record, metric) : 0;
      return Math.max(innerMax, value, outerMax);
    }, outerMax);
  }, 0);

  const safeMax = maxValue > 0 ? maxValue : 1;
  const barWidth = 16;
  const barGap = 8;
  const groupSpacing = 24;
  const groupWidth = studentCount * barWidth + Math.max(0, studentCount - 1) * barGap;
  const xStep = groupWidth + groupSpacing;
  const chartWidth = Math.max(600, padding.left + padding.right + dayLabels.length * xStep);
  const ySpan = chartHeight - padding.top - padding.bottom;
  const colors = COMPARISON_COLORS;
  const axisColor = '#cbd5f5';

  const tickCount = 4;
  const tickValues = Array.from({ length: tickCount + 1 }, (_, idx) => (safeMax / tickCount) * idx);

  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
      <svg viewBox={`0 0 ${chartWidth} ${chartHeight}`} className="block w-full" role="img" aria-label="Student comparison chart">
        <rect x={0} y={0} width={chartWidth} height={chartHeight} fill="#f8fafc" />
        <line
          x1={padding.left}
          y1={chartHeight - padding.bottom}
          x2={chartWidth - padding.right}
          y2={chartHeight - padding.bottom}
          stroke={axisColor}
          strokeWidth={1}
        />
        {tickValues.map((tick) => {
          const y = padding.top + ySpan - (tick / safeMax) * ySpan;
          return (
            <g key={`tick-${tick}`}>
              <line
                x1={padding.left}
                y1={y}
                x2={chartWidth - padding.right}
                y2={y}
                stroke="#e2e8f0"
                strokeWidth={1}
                strokeDasharray="4 6"
              />
              <text x={padding.left - 10} y={y + 4} fill="#94a3b8" fontSize="11" textAnchor="end">
                {Math.round(tick)}
              </text>
            </g>
          );
        })}

        {dayLabels.map((day, dayIndex) => {
          const baseX = padding.left + dayIndex * xStep;
          const groupOffset = (xStep - groupWidth) / 2;
          const dayLabel = new Date(day).toLocaleDateString([], { month: 'short', day: 'numeric' });

          return (
            <g key={`day-${day}`}>
              <text
                x={baseX + groupWidth / 2 + groupOffset}
                y={chartHeight - padding.bottom + 20}
                fill="#475569"
                fontSize="11"
                textAnchor="middle"
              >
                {dayLabel}
              </text>

              {valueLookup.map((series, seriesIndex) => {
                const record = series.recordMap.get(day);
                const value = record ? getMetricValue(record, metric) : 0;
                const barHeight = (value / safeMax) * ySpan;
                const barX = baseX + groupOffset + seriesIndex * (barWidth + barGap);
                const barY = padding.top + (ySpan - barHeight);
                const color = colors[seriesIndex % colors.length];

                const tooltipLines = [
                  `${series.student_name ?? `Student ${series.student_id}`}`,
                  `${METRIC_LABEL[metric]}: ${Math.round(value * 10) / 10}`,
                  dayLabel,
                ];

                return (
                  <g key={`${day}-${series.student_id}`}>
                    <rect
                      x={barX}
                      y={barY}
                      width={barWidth}
                      height={barHeight}
                      fill={color}
                      rx={4}
                    >
                      <title>{tooltipLines.join('\n')}</title>
                    </rect>
                  </g>
                );
              })}
            </g>
          );
        })}

        <text x={padding.left} y={padding.top - 12} fill="#475569" fontSize="12" fontWeight={600}>
          {METRIC_LABEL[metric]} per day
        </text>

        <text x={padding.left} y={chartHeight - 20} fill="#94a3b8" fontSize="11">
          Day
        </text>
      </svg>
    </div>
  );
};

const TeacherDashboard: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const state = location.state as LocationState | undefined;

  const school = state?.school;
  const grade = state?.grade;
  const section = state?.section ?? null;

  const [data, setData] = useState<DashboardResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [students, setStudents] = useState<Student[]>([]);
  const [studentsError, setStudentsError] = useState<string | null>(null);
  const [studentsLoading, setStudentsLoading] = useState(false);
  const [primaryStudentId, setPrimaryStudentId] = useState<number | null>(null);
  const [comparisonStudentId, setComparisonStudentId] = useState<number | null>(null);
  const [selectedMetric, setSelectedMetric] = useState<StudentMetricKey>('user_words');
  const [studentDailySeries, setStudentDailySeries] = useState<StudentDailySeries[]>([]);
  const [studentDailyLoading, setStudentDailyLoading] = useState(false);
  const [studentDailyError, setStudentDailyError] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [refreshError, setRefreshError] = useState<string | null>(null);

  const hasClassContext = Boolean(school && grade);

  useEffect(() => {
    if (!hasClassContext || !school || !grade) {
      setError('Class details are missing. Please return to the Teacher View and select a class.');
      return;
    }

    const fetchMetrics = async () => {
      try {
        setIsLoading(true);
        setRefreshError(null);
        setIsRefreshing(true);
        try {
          await refreshClassMetrics(school, grade, section ?? undefined, true);
        } catch (refreshErr: any) {
          const message = refreshErr?.message || 'Failed to refresh metrics. Showing last computed data.';
          setRefreshError(message);
        } finally {
          setIsRefreshing(false);
        }

        const response = await getClassDashboardMetrics(school, grade, section);
        setData(response);
      } catch (err: any) {
        setError(err?.message || 'Failed to load dashboard metrics.');
      } finally {
        setIsLoading(false);
      }
    };

    fetchMetrics();
  }, [hasClassContext, school, grade, section]);

  useEffect(() => {
    if (!hasClassContext || !school || !grade) {
      setStudents([]);
      setPrimaryStudentId(null);
      setComparisonStudentId(null);
      return;
    }

    const fetchStudents = async () => {
      try {
        setStudentsLoading(true);
        setStudentsError(null);
        const response = await getStudentsForClass(school, grade, section);
        const mapped = response.map((entry) => entry.student);
        const sorted = mapped
          .slice()
          .sort((a, b) => a.first_name.localeCompare(b.first_name));
        setStudents(sorted);
        setPrimaryStudentId((current) => {
          if (current && sorted.some((student) => student.id === current)) {
            return current;
          }
          return sorted[0]?.id ?? null;
        });
        setComparisonStudentId((current) =>
          current && sorted.some((student) => student.id === current) ? current : null
        );
      } catch (err: any) {
        setStudentsError(err?.message || 'Failed to load students for this class.');
      } finally {
        setStudentsLoading(false);
      }
    };

    fetchStudents();
  }, [hasClassContext, school, grade, section]);

  const topDays = useMemo(() => data?.recent_days ?? [], [data]);
  const studentSnapshots = useMemo(() => data?.student_snapshots ?? [], [data]);
  const hourlyBuckets = useMemo(() => data?.hourly_activity ?? [], [data]);
  const studentOptions = useMemo(() => students, [students]);

  useEffect(() => {
    if (!hasClassContext || !primaryStudentId) {
      setStudentDailySeries([]);
      return;
    }

    if (isRefreshing) {
      return;
    }

    const ids = [primaryStudentId];
    if (comparisonStudentId && comparisonStudentId !== primaryStudentId) {
      ids.push(comparisonStudentId);
    }

    const fetchDailyMetrics = async () => {
      try {
        setStudentDailyLoading(true);
        setStudentDailyError(null);
        const response = await getStudentDailyMetrics(school!, grade!, ids, section);
        const orderMap = new Map(ids.map((id, index) => [id, index]));
        const ordered = response.students
          .slice()
          .sort((a, b) => (orderMap.get(a.student_id) ?? 0) - (orderMap.get(b.student_id) ?? 0));
        setStudentDailySeries(ordered);
      } catch (err: any) {
        setStudentDailySeries([]);
        setStudentDailyError(err?.message || 'Failed to load student metrics.');
      } finally {
        setStudentDailyLoading(false);
      }
    };

    fetchDailyMetrics();
  }, [
    hasClassContext,
    primaryStudentId,
    comparisonStudentId,
    school,
    grade,
    section,
    isRefreshing,
  ]);

  return (
    <div className="min-h-screen bg-slate-50 py-12 px-4">
      <div className="mx-auto w-full max-w-5xl space-y-8">
        <header className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-3xl font-semibold text-slate-900">Class Dashboard</h1>
            {state && (
              <p className="mt-1 text-sm text-slate-600">
                {state.school} · Grade {state.grade}
                {state.section ? ` · Section ${state.section}` : ''}
              </p>
            )}
          </div>
          <div className="flex flex-wrap items-center justify-end gap-2">
            <button
              type="button"
              className="inline-flex items-center justify-center rounded-full border border-indigo-600 px-4 py-2 text-xs font-semibold text-indigo-600 shadow-sm transition hover:bg-indigo-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-indigo-500"
              onClick={() =>
                navigate('/class-details', {
                  state: { school, grade, section: section ?? undefined },
                })
              }
            >
              Class Details
            </button>
            <button
              type="button"
              className="inline-flex items-center justify-center rounded-full border border-indigo-600 px-4 py-2 text-xs font-semibold text-indigo-600 shadow-sm transition hover:bg-indigo-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-indigo-500"
              onClick={() =>
                navigate('/class-summary', {
                  state: { school, grade, section: section ?? undefined },
                })
              }
            >
              Class Summary
            </button>
            <button
              type="button"
              className="inline-flex items-center justify-center rounded-full px-4 py-2 text-xs font-semibold text-white shadow-lg shadow-indigo-200/60 transition bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 hover:opacity-90 focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-indigo-500"
              onClick={() => navigate('/teacher-view')}
            >
              Change Class
            </button>
          </div>
        </header>

        {!hasClassContext && (
          <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-slate-600">
            Please return to the Teacher View to pick a class before viewing the dashboard.
          </div>
        )}

        {hasClassContext && (
          <div className="space-y-8">
            {isRefreshing && (
              <div className="rounded-2xl border border-indigo-200 bg-indigo-50 p-4 text-sm text-indigo-700">
                Refreshing class metrics…
              </div>
            )}

            {refreshError && (
              <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-700">
                {refreshError}
              </div>
            )}

            {isLoading && (
              <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center text-sm text-slate-600">
                Loading dashboard metrics...
              </div>
            )}

            {error && !isLoading && (
              <div className="rounded-2xl border border-red-200 bg-red-50 p-6 text-sm text-red-700">
                {error}
              </div>
            )}

            {!isLoading && !error && data && (
              <>
                <section className="grid gap-4 md:grid-cols-3">
                  <article className="rounded-2xl bg-white p-6 shadow-sm">
                    <h2 className="text-sm font-semibold text-slate-500">Total Conversations</h2>
                    <p className="mt-2 text-3xl font-semibold text-slate-900">
                      {formatNumber(data.class_summary?.total_conversations)}
                    </p>
                    <p className="mt-1 text-xs text-slate-500">
                      Across cohort window {data.class_summary?.cohort_start} to {data.class_summary?.cohort_end}
                    </p>
                  </article>
                  <article className="rounded-2xl bg-white p-6 shadow-sm">
                    <h2 className="text-sm font-semibold text-slate-500">Total Minutes</h2>
                    <p className="mt-2 text-3xl font-semibold text-slate-900">
                      {formatMinutes(data.class_summary?.total_minutes)}
                    </p>
                    <p className="mt-1 text-xs text-slate-500">Sessionized minutes spent with the coach</p>
                  </article>
                  <article className="rounded-2xl bg-white p-6 shadow-sm">
                    <h2 className="text-sm font-semibold text-slate-500">After-school Conversations</h2>
                    <p className="mt-2 text-3xl font-semibold text-slate-900">
                      {formatNumber(data.class_summary?.after_school_conversations)}
                    </p>
                    <p className="mt-1 text-xs text-slate-500">
                      {data.class_summary?.after_school_user_pct != null
                        ? `${formatPercent(data.class_summary?.after_school_user_pct)} of user messages outside school hours`
                        : 'Messages flagged as outside school hours'}
                    </p>
                  </article>
                </section>

                <section className="rounded-2xl bg-white p-6 shadow-sm">
                  <div className="flex items-center justify-between gap-2">
                    <h2 className="text-lg font-semibold text-slate-900">Top Days</h2>
                    <span className="text-xs font-medium text-slate-500">
                      Top {topDays.length} days by user messages
                    </span>
                  </div>
                  {topDays.length === 0 ? (
                    <p className="mt-3 text-sm text-slate-500">No daily stats yet. Refresh the metrics to populate this view.</p>
                  ) : (
                    <div className="mt-4 overflow-x-auto">
                      <table className="min-w-full divide-y divide-slate-200 text-sm">
                        <thead className="bg-slate-50">
                          <tr>
                            <th className="py-2 text-left font-semibold text-slate-600">Day</th>
                            <th className="py-2 text-left font-semibold text-slate-600">Minutes</th>
                            <th className="py-2 text-left font-semibold text-slate-600">User Msgs</th>
                            <th className="py-2 text-left font-semibold text-slate-600">AI Msgs</th>
                            <th className="py-2 text-left font-semibold text-slate-600">Avg Depth</th>
                            <th className="py-2 text-left font-semibold text-slate-600">Relevant Questions</th>
                            <th className="py-2 text-left font-semibold text-slate-600">Active Students</th>
                            <th className="py-2 text-left font-semibold text-slate-600">After-school Convos</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                          {topDays.map((day) => (
                            <tr key={day.day}>
                              <td className="py-2 text-slate-700">{formatDayLabel(day.day)}</td>
                              <td className="py-2 text-slate-700">{formatMinutes(day.total_minutes)}</td>
                              <td className="py-2 text-slate-700">{formatNumber(day.total_user_messages)}</td>
                              <td className="py-2 text-slate-700">{formatNumber(day.total_ai_messages)}</td>
                              <td className="py-2 text-slate-700">{formatOneDecimal(day.avg_depth)}</td>
                              <td className="py-2 text-slate-700">{formatNumber(day.total_relevant_questions)}</td>
                              <td className="py-2 text-slate-700">{formatNumber(day.active_students)}</td>
                              <td className="py-2 text-slate-700">{formatNumber(day.after_school_conversations)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </section>

                <section className="rounded-2xl bg-white p-6 shadow-sm">
                  <div className="flex items-center justify-between gap-2">
                    <h2 className="text-lg font-semibold text-slate-900">Students (Top 10 by Avg Words per Message)</h2>
                  </div>
                  {studentSnapshots.length === 0 ? (
                    <p className="mt-3 text-sm text-slate-500">No student-level snapshots yet.</p>
                  ) : (
                    <div className="mt-4 overflow-x-auto">
                      <table className="min-w-full divide-y divide-slate-200 text-sm">
                        <thead className="bg-slate-50">
                          <tr>
                            <th className="py-2 text-left font-semibold text-slate-600">Student</th>
                            <th className="py-2 text-left font-semibold text-slate-600">Avg Words/Msg</th>
                            <th className="py-2 text-left font-semibold text-slate-600">Avg Depth</th>
                            <th className="py-2 text-left font-semibold text-slate-600">Relevant Questions</th>
                            <th className="py-2 text-left font-semibold text-slate-600">User Msgs</th>
                            <th className="py-2 text-left font-semibold text-slate-600">Words Typed</th>
                            <th className="py-2 text-left font-semibold text-slate-600">Minutes</th>
                            <th className="py-2 text-left font-semibold text-slate-600">After-school %</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                          {studentSnapshots.map((snapshot) => (
                            <tr key={snapshot.student_id}>
                              <td className="py-2 text-slate-700">
                                {snapshot.student_name ?? `Student ${snapshot.student_id}`}
                              </td>
                              <td className="py-2 text-slate-700">{formatOneDecimal(snapshot.avg_words_per_message)}</td>
                              <td className="py-2 text-slate-700">{formatOneDecimal(snapshot.avg_depth)}</td>
                              <td className="py-2 text-slate-700">{formatNumber(snapshot.total_relevant_questions)}</td>
                              <td className="py-2 text-slate-700">{formatNumber(snapshot.total_user_messages)}</td>
                              <td className="py-2 text-slate-700">{formatNumber(snapshot.total_user_words)}</td>
                              <td className="py-2 text-slate-700">{formatMinutes(snapshot.total_minutes)}</td>
                              <td className="py-2 text-slate-700">{formatPercent(snapshot.after_school_user_pct)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </section>

                <section className="rounded-2xl bg-white p-6 shadow-sm">
                  <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                    <div>
                      <h2 className="text-lg font-semibold text-slate-900">Student Comparison</h2>
                      <p className="mt-1 text-sm text-slate-500">
                        Compare per-day engagement metrics for one or two students in this class.
                      </p>
                    </div>
                    <div className="flex flex-wrap items-end gap-3">
                      <label className="flex flex-col text-xs font-semibold uppercase tracking-wide text-slate-500">
                        Student A
                        <select
                          className="mt-1 min-w-[12rem] rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40"
                          value={primaryStudentId ?? ''}
                          onChange={(event) => {
                            const value = event.target.value;
                            setPrimaryStudentId(value ? Number(value) : null);
                          }}
                        >
                          <option value="" disabled>
                            Select a student
                          </option>
                          {studentOptions.map((student) => (
                            <option key={student.id} value={student.id}>
                              {student.first_name} (Roll {student.roll_number})
                            </option>
                          ))}
                        </select>
                      </label>
                      <label className="flex flex-col text-xs font-semibold uppercase tracking-wide text-slate-500">
                        Student B (optional)
                        <select
                          className="mt-1 min-w-[12rem] rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40"
                          value={comparisonStudentId ?? ''}
                          onChange={(event) => {
                            const value = event.target.value;
                            setComparisonStudentId(value ? Number(value) : null);
                          }}
                        >
                          <option value="">No comparison</option>
                          {studentOptions.map((student) => (
                            <option
                              key={student.id}
                              value={student.id}
                              disabled={student.id === primaryStudentId}
                            >
                              {student.first_name} (Roll {student.roll_number})
                            </option>
                          ))}
                        </select>
                      </label>
                      <label className="flex flex-col text-xs font-semibold uppercase tracking-wide text-slate-500">
                        Metric
                        <select
                          className="mt-1 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40"
                          value={selectedMetric}
                          onChange={(event) => setSelectedMetric(event.target.value as StudentMetricKey)}
                        >
                          {METRIC_OPTIONS.map((option) => (
                            <option key={option.value} value={option.value}>
                              {option.label}
                            </option>
                          ))}
                        </select>
                      </label>
                    </div>
                  </div>

                  {studentsLoading ? (
                    <p className="mt-6 text-sm text-slate-500">Loading students…</p>
                  ) : studentsError ? (
                    <div className="mt-6 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
                      {studentsError}
                    </div>
                  ) : !primaryStudentId || studentOptions.length === 0 ? (
                    <p className="mt-6 text-sm text-slate-500">Select at least one student to see per-day metrics.</p>
                  ) : studentDailyLoading ? (
                    <p className="mt-6 text-sm text-slate-500">Loading daily metrics…</p>
                  ) : studentDailyError ? (
                    <div className="mt-6 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
                      {studentDailyError}
                    </div>
                  ) : studentDailySeries.length === 0 ? (
                    <p className="mt-6 text-sm text-slate-500">
                      No daily metrics recorded yet for the selected student{comparisonStudentId ? 's' : ''}.
                    </p>
                  ) : (
                    <div className="mt-6 space-y-4">
                      <div className="flex flex-wrap gap-4 text-xs">
                        {studentDailySeries.map((series, index) => (
                          <span
                            key={series.student_id}
                            className="inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1 font-medium text-slate-700"
                          >
                            <span
                              className="h-2.5 w-2.5 rounded-full"
                              style={{ backgroundColor: COMPARISON_COLORS[index % COMPARISON_COLORS.length] }}
                            />
                            {series.student_name ?? `Student ${series.student_id}`}
                          </span>
                        ))}
                      </div>
                      <StudentComparisonChart data={studentDailySeries} metric={selectedMetric} />
                    </div>
                  )}
                </section>

                <section className="rounded-2xl bg-white p-6 shadow-sm">
                  <div className="flex items-center justify-between gap-2">
                    <h2 className="text-lg font-semibold text-slate-900">Hourly Activity (Last 24h)</h2>
                  </div>
                  {hourlyBuckets.length === 0 ? (
                    <p className="mt-3 text-sm text-slate-500">No hourly records yet. Refresh the metrics to populate this view.</p>
                  ) : (
                    <div className="mt-4">
                      <HourlyActivityChart buckets={hourlyBuckets} />
                    </div>
                  )}
                </section>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default TeacherDashboard;
  const getMetricValue = (record: StudentDailyRecord, key: StudentMetricKey): number => {
    const raw = record[key];
    if (raw === null || raw === undefined) {
      return 0;
    }
    return typeof raw === 'number' ? raw : Number(raw) || 0;
  };
