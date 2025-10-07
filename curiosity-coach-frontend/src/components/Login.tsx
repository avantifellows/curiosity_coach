import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { loginUser } from '../services/api';

const Login: React.FC = () => {
  const [identifier, setIdentifier] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const { login } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      // Call the API to login with identifier (phone or name)
      const response = await loginUser(identifier);
      if (response.success && response.user) {
        login(response.user);
        
        // Preserve query parameters during navigation
        const queryParams = new URLSearchParams(location.search);
        const targetPath = queryParams.toString() ? `/chat?${queryParams.toString()}` : '/chat';
        navigate(targetPath);
      } else {
        setError(response.message || 'Login failed');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to log in');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-8 sm:py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-6 sm:space-y-8">
        <div>
          <h2 className="mt-6 text-center text-2xl sm:text-3xl font-extrabold text-gray-900">
            Curiosity Coach
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            Sign in to start your learning journey
          </p>
        </div>
        
        <form className="mt-6 sm:mt-8 space-y-4 sm:space-y-6" onSubmit={handleSubmit}>
          <div>
            <label htmlFor="identifier" className="sr-only">Name or Phone Number</label>
            <input
              id="identifier"
              name="identifier"
              type="text"
              autoComplete="off"
              required
              className="appearance-none relative block w-full px-3 py-3 sm:py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-md focus:outline-hidden focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 text-base sm:text-sm"
              placeholder="Your name or phone number"
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
            />
            <p className="mt-1 text-xs text-gray-500">Enter your name (e.g., Surya) or phone number</p>
          </div>

          {error && (
            <div className="text-red-500 text-sm text-center px-2">{error}</div>
          )}

          <div>
            <button
              type="submit"
              disabled={isLoading}
              className="group relative w-full flex justify-center py-3 sm:py-2 px-4 border border-transparent text-base sm:text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-hidden focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? 'Signing in...' : 'Sign in'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default Login; 