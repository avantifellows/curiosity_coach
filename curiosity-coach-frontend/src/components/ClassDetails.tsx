import React, { useEffect, useMemo, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { StudentWithConversation } from '../types';
import { getStudentsForClass } from '../services/api';

interface ClassDetailsState {
  school?: string;
  grade?: number | string;
  section?: string;
}

const ClassDetails: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const state = (location.state as ClassDetailsState) || {};

  const { school, grade, section } = state;
  const [students, setStudents] = useState<StudentWithConversation[] | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
          setError('Failed to fetch students. Please try again.');
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

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-8 px-4">
      <div className="max-w-lg w-full bg-white p-8 rounded-lg shadow space-y-4 text-center">
        <h1 className="text-3xl font-bold text-gray-900">Class Details</h1>
        <p className="text-lg text-gray-700">Welcome!</p>
        {(school || grade || section) && (
          <div className="text-left space-y-1 text-gray-700">
            {school && <p><span className="font-semibold">School:</span> {school}</p>}
            {gradeNumber && <p><span className="font-semibold">Grade:</span> {gradeNumber}</p>}
            {section && <p><span className="font-semibold">Section:</span> {section}</p>}
          </div>
        )}
        {!school && !grade && !section && (
          <p className="text-sm text-gray-500">
            No class info provided. Return to the teacher view to enter details.
          </p>
        )}
        <div className="text-left space-y-2">
          {isLoading && <p className="text-sm text-gray-500">Loading students...</p>}
          {error && <p className="text-sm text-red-600">{error}</p>}
          {!isLoading && !error && students && (
            <>
              {students.length === 0 ? (
                <p className="text-sm text-gray-500">No students found for this class.</p>
              ) : (
                <div className="space-y-2">
                  <p className="font-semibold text-gray-800">
                    {students.length} student{students.length === 1 ? '' : 's'} found
                  </p>
                  <ul className="divide-y divide-gray-200 border border-gray-100 rounded-md">
                    {students.map(({ student, latest_conversation }) => {
                      const lastUpdated = latest_conversation?.updated_at
                        ? new Date(latest_conversation.updated_at).toLocaleString()
                        : null;
                      return (
                        <li
                          key={student.id}
                          className="px-4 py-3 text-sm text-gray-700 space-y-3"
                        >
                          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                            <div>
                              <span className="font-medium">{student.first_name}</span>
                              <span className="text-gray-500 ml-2">Roll #{student.roll_number}</span>
                            </div>
                            <div className="text-xs text-gray-500 text-left sm:text-right">
                              {latest_conversation ? (
                                <>
                                  <p className="font-semibold text-gray-600">
                                    Last chat: {latest_conversation.title || 'Untitled'}
                                  </p>
                                  <p>{lastUpdated}</p>
                                </>
                              ) : (
                                <p>No conversations yet</p>
                              )}
                            </div>
                          </div>
                          {latest_conversation && (
                            <div className="flex justify-end">
                              <button
                                type="button"
                                className="inline-flex items-center gap-2 px-4 py-1.5 text-xs font-semibold rounded-full text-white bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 shadow-lg shadow-indigo-200/60 hover:opacity-90 focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-indigo-500"
                                onClick={() =>
                                  navigate('/class-conversation', {
                                    state: {
                                      studentName: student.first_name,
                                      conversation: latest_conversation,
                                    },
                                  })
                                }
                              >
                                <span>View Conversation</span>
                              </button>
                            </div>
                          )}
                        </li>
                      );
                    })}
                  </ul>
                </div>
              )}
            </>
          )}
        </div>
        <button
          onClick={() => navigate('/teacher-view')}
          className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
        >
          Back to Teacher View
        </button>
      </div>
    </div>
  );
};

export default ClassDetails;

