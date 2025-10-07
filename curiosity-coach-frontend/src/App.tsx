import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ChatProvider } from './context/ChatContext';
import Login from './components/Login';
import ChatInterface from './components/ChatInterface';
import PromptVersionsView from './components/PromptVersionsView';

// Protected route component
const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, isLoading } = useAuth();
  const location = useLocation();
  
  if (isLoading) {
    return <div className="flex justify-center items-center min-h-screen">Loading...</div>;
  }
  
  if (!user) {
    // Preserve query parameters when redirecting to login
    const targetPath = location.search ? `/${location.search}` : '/';
    return <Navigate to={targetPath} replace />;
  }
  
  return <>{children}</>;
};

const App: React.FC = () => {
  return (
    <AuthProvider>
      <Router>
        <ChatProvider>
          <div className="min-h-screen bg-gray-50">
            <Routes>
              <Route path="/" element={<Login />} />
              <Route
                path="/chat"
                element={
                  <ProtectedRoute>
                    <ChatInterface mode="chat" />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/test-prompt"
                element={
                  <ProtectedRoute>
                    <ChatInterface mode="test-prompt" />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/prompts"
                element={
                  <ProtectedRoute>
                    <PromptVersionsView />
                  </ProtectedRoute>
                }
              />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </div>
        </ChatProvider>
      </Router>
    </AuthProvider>
  );
};

export default App;
