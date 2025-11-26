import React, { useEffect, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { loginUser, loginStudent, getStudentOptions } from '../services/api';
import { StudentOptions } from '../types';

const Login: React.FC = () => {
  const [identifier, setIdentifier] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const { login } = useAuth();

  // Student login state
  const [school, setSchool] = useState('');
  const [grade, setGrade] = useState<number | ''>('');
  const [section, setSection] = useState('');
  const [rollNumber, setRollNumber] = useState<number | ''>('');
  const [firstName, setFirstName] = useState('');

  // Debug mode detection from URL query params
  const searchParams = new URLSearchParams(location.search);
  const debugMode = searchParams.get('debug') === 'true';

  const [studentOptions, setStudentOptions] = useState<StudentOptions | null>(null);
  const [studentOptionsLoading, setStudentOptionsLoading] = useState(false);
  const [studentOptionsError, setStudentOptionsError] = useState<string | null>(null);

  useEffect(() => {
    if (debugMode) {
      return;
    }

    let isMounted = true;

    const fetchOptions = async () => {
      setStudentOptionsLoading(true);
      setStudentOptionsError(null);
      try {
        const options = await getStudentOptions();
        if (isMounted) {
          setStudentOptions(options);
        }
      } catch (err) {
        console.error('Failed to fetch student options:', err);
        if (isMounted) {
          setStudentOptionsError('Failed to load student options. Please refresh the page.');
        }
      } finally {
        if (isMounted) {
          setStudentOptionsLoading(false);
        }
      }
    };

    fetchOptions();

    return () => {
      isMounted = false;
    };
  }, [debugMode]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      if (debugMode) {
        // Debug mode: use identifier-based login
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
      } else {
        // Student mode: use student login
        if (!school || grade === '' || rollNumber === '' || !firstName) {
          setError('Please fill in all required fields');
          setIsLoading(false);
          return;
        }

        const response = await loginStudent({
          school,
          grade: Number(grade),
          section: section || null,
          roll_number: Number(rollNumber),
          first_name: firstName
        });

        if (response.success && response.user) {
          // Merge student data into user object for localStorage
          const userWithStudent = {
            ...response.user,
            student: response.student
          };
          login(userWithStudent);

          // Preserve query parameters during navigation
          const queryParams = new URLSearchParams(location.search);
          const targetPath = queryParams.toString() ? `/chat?${queryParams.toString()}` : '/chat';
          navigate(targetPath);
        } else {
          setError(response.message || 'Student login failed');
        }
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
          {debugMode ? (
            // Debug mode: Simple identifier input
            <div>
              <label htmlFor="identifier" className="sr-only">User ID</label>
              <input
                id="identifier"
                name="identifier"
                type="text"
                autoComplete="off"
                required
                className="appearance-none relative block w-full px-3 py-3 sm:py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-md focus:outline-hidden focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 text-base sm:text-sm"
                placeholder="User ID"
                value={identifier}
                onChange={(e) => setIdentifier(e.target.value)}
              />
              <p className="mt-1 text-xs text-gray-500">Developer mode: Enter user ID for testing</p>
            </div>
          ) : (
            // Student mode: Multiple fields
            <>
              {studentOptionsLoading && (
                <div className="text-sm text-gray-500 text-center">
                  Loading school details...
                </div>
              )}
              {studentOptionsError && (
                <div className="text-sm text-red-600 text-center">
                  {studentOptionsError}
                </div>
              )}
              <div>
                <label htmlFor="school" className="block text-sm font-medium text-gray-700 mb-1">
                  School *
                </label>
                <select
                  id="school"
                  name="school"
                  required
                  className="appearance-none relative block w-full px-3 py-3 sm:py-2 border border-gray-300 text-gray-900 rounded-md focus:outline-hidden focus:ring-indigo-500 focus:border-indigo-500 text-base sm:text-sm"
                  value={school}
                  onChange={(e) => setSchool(e.target.value)}
                  disabled={!studentOptions}
                >
                  <option value="">Select your school</option>
                  {studentOptions?.schools.map((s) => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
                <p className="mt-1 text-xs text-gray-500">Choose your school from the list</p>
              </div>

              <div>
                <label htmlFor="grade" className="block text-sm font-medium text-gray-700 mb-1">
                  Grade *
                </label>
                <select
                  id="grade"
                  name="grade"
                  required
                  className="appearance-none relative block w-full px-3 py-3 sm:py-2 border border-gray-300 text-gray-900 rounded-md focus:outline-hidden focus:ring-indigo-500 focus:border-indigo-500 text-base sm:text-sm"
                  value={grade}
                  onChange={(e) => setGrade(Number(e.target.value))}
                  disabled={!studentOptions}
                >
                  <option value="">Select your grade</option>
                  {studentOptions?.grades.map((g) => (
                    <option key={g} value={g}>Grade {g}</option>
                  ))}
                </select>
                <p className="mt-1 text-xs text-gray-500">Select your current grade (3 to 10)</p>
              </div>

              <div>
                <label htmlFor="section" className="block text-sm font-medium text-gray-700 mb-1">
                  Section (Optional)
                </label>
                <select
                  id="section"
                  name="section"
                  className="appearance-none relative block w-full px-3 py-3 sm:py-2 border border-gray-300 text-gray-900 rounded-md focus:outline-hidden focus:ring-indigo-500 focus:border-indigo-500 text-base sm:text-sm"
                  value={section}
                  onChange={(e) => setSection(e.target.value)}
                  disabled={!studentOptions}
                >
                  <option value="">No section / Not applicable</option>
                  {studentOptions?.sections.map((s) => (
                    <option key={s} value={s}>Section {s}</option>
                  ))}
                </select>
                <p className="mt-1 text-xs text-gray-500">Select your section if your school has sections (A, B, C, etc.)</p>
              </div>

              <div>
                <label htmlFor="rollNumber" className="block text-sm font-medium text-gray-700 mb-1">
                  Roll Number *
                </label>
                <input
                  id="rollNumber"
                  name="rollNumber"
                  type="number"
                  min="1"
                  max="100"
                  required
                  className="appearance-none relative block w-full px-3 py-3 sm:py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-md focus:outline-hidden focus:ring-indigo-500 focus:border-indigo-500 text-base sm:text-sm"
                  placeholder="Enter your roll number"
                  value={rollNumber}
                  onChange={(e) => setRollNumber(e.target.value ? Number(e.target.value) : '')}
                />
                <p className="mt-1 text-xs text-gray-500">Your roll number in your class</p>
              </div>

              <div>
                <label htmlFor="firstName" className="block text-sm font-medium text-gray-700 mb-1">
                  First Name *
                </label>
                <input
                  id="firstName"
                  name="firstName"
                  type="text"
                  autoComplete="given-name"
                  required
                  className="appearance-none relative block w-full px-3 py-3 sm:py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-md focus:outline-hidden focus:ring-indigo-500 focus:border-indigo-500 text-base sm:text-sm"
                  placeholder="Enter your first name"
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                />
                <p className="mt-1 text-xs text-gray-500">Enter your first name (e.g., Amit, Priya)</p>
              </div>
            </>
          )}

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