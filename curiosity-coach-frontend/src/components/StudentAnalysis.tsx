import React, { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Student } from '../types';
import { analyzeStudentConversations } from '../services/api';
import parse from 'html-react-parser';

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
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisError, setAnalysisError] = useState<string | null>(null);

  useEffect(() => {
    if (!student) {
      navigate('/teacher-view', { replace: true });
      return;
    }

    let isMounted = true;
    const fetchAnalysis = async () => {
      setIsAnalyzing(true);
      setAnalysisError(null);
      setAnalysis(null); // Clear previous analysis
      try {
        const data = await analyzeStudentConversations(student.id);
        console.log('Student analysis response received:', data);
        if (isMounted) {
          setAnalysis(data.analysis || '');
          console.log('Student analysis set to state:', data.analysis);
        }
      } catch (err) {
        console.error('Failed to analyze student conversations:', err);
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
  }, [student, navigate]);

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
            {isAnalyzing && (
              <AnalysisLoading key="analysis-loading" />
            )}
            
            {analysisError && (
              <div className="rounded-lg bg-red-50 p-4">
                <p className="text-sm text-red-600">{analysisError}</p>
              </div>
            )}

            {!isAnalyzing && !analysisError && analysis && (
              <div className="text-slate-700 leading-relaxed">
                {parse(analysis)}
              </div>
            )}

            {!isAnalyzing && !analysisError && !analysis && (
              <div className="rounded-lg bg-yellow-50 p-4">
                <p className="text-sm text-yellow-700">Analysis completed but no content received.</p>
              </div>
            )}
          </section>

          <button
            onClick={() => navigate('/class-conversation', { state: { student } })}
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

