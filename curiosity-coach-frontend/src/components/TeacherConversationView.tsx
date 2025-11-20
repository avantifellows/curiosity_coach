import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { ConversationWithMessages } from '../types';

interface ConversationLocationState {
  studentName?: string;
  conversation?: ConversationWithMessages | null;
}

const TeacherConversationView: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const state = (location.state as ConversationLocationState) || {};
  const conversation = state.conversation;
  const studentName = state.studentName;

  if (!conversation) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
        <div className="max-w-md w-full bg-white rounded-lg shadow p-6 space-y-4 text-center">
          <p className="text-gray-700">No conversation selected.</p>
          <button
            onClick={() => navigate(-1)}
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
          >
            Back
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4">
      <div className="max-w-3xl mx-auto bg-white rounded-lg shadow p-6 space-y-6">
        <div>
          <button
            onClick={() => navigate(-1)}
            className="text-sm text-indigo-600 hover:text-indigo-700"
          >
            ← Back
          </button>
          <h1 className="mt-2 text-2xl font-bold text-gray-900">
            {studentName ? `${studentName}'s conversation` : 'Conversation'}
          </h1>
          <p className="text-sm text-gray-500">
            {conversation.title || 'Untitled conversation'} · Last updated{' '}
            {new Date(conversation.updated_at).toLocaleString()}
          </p>
        </div>
        <div className="border border-gray-200 rounded-md max-h-[70vh] overflow-y-auto space-y-4 p-4 bg-gray-50">
          {conversation.messages.length === 0 ? (
            <p className="text-sm text-gray-500">No messages yet.</p>
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
                  className={`mt-1 rounded-lg px-4 py-2 shadow-sm ${
                    message.is_user ? 'bg-white border border-indigo-100' : 'bg-green-50 border border-green-100'
                  }`}
                >
                  <p className="text-sm text-gray-800">{message.content}</p>
                  <p className="mt-1 text-xs text-gray-400">
                    {new Date(message.timestamp).toLocaleString()}
                  </p>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};

export default TeacherConversationView;

