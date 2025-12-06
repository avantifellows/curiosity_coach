import React, { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { ConversationWithMessages, Student } from '../types';
import { getAllStudentConversations } from '../services/api';

interface StudentAnalysisState {
  student?: Student;
}

const StudentAnalysis: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const state = (location.state as StudentAnalysisState) || {};
  const student = state.student;

  const [conversations, setConversations] = useState<ConversationWithMessages[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!student) {
      navigate('/teacher-view', { replace: true });
      return;
    }

    let isMounted = true;
    const fetchConversations = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const data = await getAllStudentConversations(student.id);
        if (isMounted) {
          setConversations(data);
        }
      } catch (err) {
        console.error('Failed to fetch student conversations:', err);
        if (isMounted) {
          setError('Failed to fetch conversations. Please try again.');
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    fetchConversations();

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
            {isLoading && <p className="text-sm text-slate-500">Loading conversations...</p>}
            {error && <p className="text-sm text-red-600">{error}</p>}

            {!isLoading && !error && (
              <>
                {conversations.length === 0 ? (
                  <p className="text-sm text-slate-500">No conversations found for this student.</p>
                ) : (
                  <div className="space-y-8">
                    {conversations.map((conversation, index) => (
                      <div
                        key={conversation.id}
                        className="space-y-2"
                      >
                        <h2 className="text-xl font-semibold text-slate-900">
                          Conversation {index + 1}: {conversation.title || 'Untitled'}
                        </h2>
                        <div className="space-y-2 pl-4">
                          {conversation.messages.length === 0 ? (
                            <p className="text-slate-500">No messages</p>
                          ) : (
                            conversation.messages.map((message, msgIndex) => (
                              <p
                                key={message.id || msgIndex}
                                className="text-slate-700 whitespace-pre-wrap"
                              >
                                <span className="font-semibold">
                                  {message.is_user ? 'Student: ' : 'AI: '}
                                </span>
                                {message.content}
                              </p>
                            ))
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </>
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

