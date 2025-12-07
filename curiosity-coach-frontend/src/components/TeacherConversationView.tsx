import React, { useCallback, useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { ConversationWithMessages, Student } from '../types';
import { getStudentConversations } from '../services/api';

interface ConversationLocationState {
  student?: Student;
}

const PAGE_SIZE = 3;

const TeacherConversationView: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const state = (location.state as ConversationLocationState) || {};
  const student = state.student;
  const [conversations, setConversations] = useState<ConversationWithMessages[]>([]);
  const [nextOffset, setNextOffset] = useState<number | null>(null);
  const [isInitialLoading, setIsInitialLoading] = useState(false);
  const [isLoadMore, setIsLoadMore] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchConversations = useCallback(
    async (offset = 0) => {
      if (!student) {
        return;
      }
      if (offset === 0) {
        setIsInitialLoading(true);
      } else {
        setIsLoadMore(true);
      }
      setError(null);
      try {
        const data = await getStudentConversations(student.id, PAGE_SIZE, offset);
        setConversations((prev) => (offset === 0 ? data.conversations : [...prev, ...data.conversations]));
        setNextOffset(data.next_offset);
      } catch (err) {
        console.error(err);
        setError(err instanceof Error ? err.message : 'Failed to fetch conversations.');
      } finally {
        setIsInitialLoading(false);
        setIsLoadMore(false);
      }
    },
    [student]
  );

  useEffect(() => {
    if (!student) {
      setError('No student selected.');
      return;
    }
    fetchConversations(0);
  }, [student, fetchConversations]);

  const handleLoadMore = () => {
    if (nextOffset == null || isLoadMore) {
      return;
    }
    fetchConversations(nextOffset);
  };

  if (!student) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 px-4">
        <div className="max-w-md w-full bg-white rounded-2xl shadow p-6 space-y-4 text-center">
          <p className="text-slate-700">No student selected.</p>
          <button
            onClick={() => navigate(-1)}
            className="inline-flex items-center justify-center rounded-full bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow hover:bg-indigo-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-indigo-500"
          >
            Back
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 py-10 px-4">
      <div className="mx-auto flex w-full max-w-4xl flex-col gap-6">
        <div className="rounded-3xl bg-white p-6 shadow-lg shadow-slate-200">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1">
              <button
                onClick={() => navigate(-1)}
                className="text-sm font-semibold text-indigo-600 transition hover:text-indigo-700"
              >
                ← Back
              </button>
              <h1 className="mt-3 text-3xl font-semibold text-slate-900">{student.first_name}&rsquo;s conversations</h1>
              <p className="text-sm text-slate-500">History ordered by most recent chats first.</p>
            </div>
            <button
              type="button"
              className="inline-flex items-center justify-center rounded-full px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-indigo-200/60 transition bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 hover:opacity-90 focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-indigo-500 whitespace-nowrap"
              onClick={() => {
                navigate('/student-analysis', {
                  state: { student },
                });
              }}
            >
              Analyze Kid
            </button>
          </div>
        </div>

        <div className="rounded-3xl bg-white p-6 shadow-lg shadow-slate-200 space-y-6">
          {error && (
            <div className="rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700">
              {error}
            </div>
          )}

          {isInitialLoading ? (
            <p className="text-sm text-slate-500">Loading conversations...</p>
          ) : conversations.length === 0 ? (
            <p className="text-sm text-slate-500">No conversations yet.</p>
          ) : (
            <ul className="space-y-6">
              {conversations.map((conversation) => (
                <li key={conversation.id} className="rounded-2xl border border-slate-100 p-5 shadow-sm">
                  <div className="flex flex-col gap-2 border-b border-slate-100 pb-4 sm:flex-row sm:items-center sm:justify-between">
                    <div>
                      <p className="text-lg font-semibold text-slate-900">
                        {conversation.title || 'Untitled conversation'}
                      </p>
                      <p className="text-xs uppercase tracking-wide text-slate-500">Conversation #{conversation.id}</p>
                    </div>
                    <p className="text-sm text-slate-500">
                      Last updated {new Date(conversation.updated_at).toLocaleString()}
                    </p>
                  </div>
                  <div className="mt-4 max-h-[40vh] space-y-4 overflow-y-auto pr-1">
                    {conversation.messages.length === 0 ? (
                      <p className="text-sm text-slate-500">No messages yet.</p>
                    ) : (
                      conversation.messages.map((message) => (
                        <div
                          key={message.id}
                          className={`flex flex-col ${
                            message.is_user ? 'items-start text-indigo-700' : 'items-end text-green-700'
                          }`}
                        >
                          <span className="text-xs uppercase font-semibold tracking-wide">
                            {message.is_user ? 'Kid' : 'Coach'}
                          </span>
                          <div
                            className={`mt-1 rounded-2xl px-4 py-2 shadow-sm ${
                              message.is_user ? 'bg-white border border-indigo-100' : 'bg-green-50 border border-green-100'
                            }`}
                          >
                            <p className="text-sm text-slate-800">{message.content}</p>
                            <p className="mt-1 text-xs text-slate-400">
                              {new Date(message.timestamp).toLocaleString()}
                            </p>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}

          {nextOffset !== null && conversations.length > 0 && (
            <button
              onClick={handleLoadMore}
              disabled={isLoadMore}
              className="inline-flex w-full items-center justify-center rounded-full bg-slate-900 px-6 py-3 text-sm font-semibold text-white shadow transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
            >
              {isLoadMore ? 'Loading...' : 'Load more conversations'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default TeacherConversationView;

