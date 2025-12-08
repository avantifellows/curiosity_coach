import React, { useEffect, useMemo, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { StudentWithConversation, ConversationWithMessages } from '../types';
import { getStudentsForClass, analyzeClassConversations } from '../services/api';
import parse from 'html-react-parser';

// AnalysisLoading component (inline to avoid module resolution issues)
const AnalysisLoading: React.FC<{ message?: string; videoPath?: string }> = ({ 
  message = "PROCESSING",
  videoPath = "/analysis-loading.mp4"
}) => {
  const videoRef = React.useRef<HTMLVideoElement>(null);

  React.useEffect(() => {
    return () => {
      // Cleanup: pause and reset video when component unmounts
      if (videoRef.current) {
        videoRef.current.pause();
        videoRef.current.src = '';
        videoRef.current.load();
      }
    };
  }, []);

  return (
    <div className="flex flex-col items-center justify-center py-12 px-4">
      <div className="max-w-md w-full space-y-6">
        <div className="relative w-full aspect-video rounded-lg overflow-hidden bg-slate-100 shadow-lg">
          <video
            ref={videoRef}
            autoPlay
            loop
            muted
            playsInline
            className="w-full h-full object-cover"
          >
            <source src={videoPath} type="video/mp4" />
          </video>
        </div>
        <div className="text-center">
          <p className="text-lg font-medium text-slate-700 animate-pulse">
            {message}
          </p>
        </div>
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
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisError, setAnalysisError] = useState<string | null>(null);

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

  // Fetch analysis when students are loaded
  useEffect(() => {
    if (!students || students.length === 0 || !school || !gradeNumber || !section) {
      return;
    }

    // Check if any students have conversations
    const hasConversations = students.some(
      ({ latest_conversation }) => latest_conversation !== null && latest_conversation !== undefined
    );

    if (!hasConversations) {
      return;
    }

    let isMounted = true;
    const fetchAnalysis = async () => {
      setIsAnalyzing(true);
      setAnalysisError(null);
      setAnalysis(null); // Clear previous analysis
      try {
        const data = await analyzeClassConversations(school, gradeNumber, section);
        console.log('Analysis response received:', data);
        if (isMounted) {
          setAnalysis(data.analysis || '');
          console.log('Analysis set to state:', data.analysis);
        }
      } catch (err) {
        console.error('Failed to analyze class conversations:', err);
        if (isMounted) {
          setAnalysisError(err instanceof Error ? err.message : 'Failed to generate analysis. Please try again.');
        }
      } finally {
        if (isMounted) {
          setIsAnalyzing(false);
          console.log('isAnalyzing set to false');
        }
      }
    };

    fetchAnalysis();

    return () => {
      isMounted = false;
    };
  }, [students, school, gradeNumber, section]);

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
                    {isAnalyzing && (
                      <AnalysisLoading key="analysis-loading" message="PROCESSING" />
                    )}
                    {analysisError && (
                      <div className="rounded-lg bg-red-50 p-4">
                        <p className="text-sm text-red-700">{analysisError}</p>
                      </div>
                    )}
                    {!isAnalyzing && analysis && (
                      <div className="space-y-4">
                        <h2 className="text-2xl font-semibold text-slate-900">Class Analysis</h2>
                        <div className="rounded-lg bg-slate-50 p-6">
                          <div className="text-slate-700 leading-relaxed">
                            {parse(analysis)}
                          </div>
                        </div>
                      </div>
                    )}
                    {!isAnalyzing && !analysis && !analysisError && (
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

