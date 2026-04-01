import React, { useEffect, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { AutoAwesomeRounded } from '@mui/icons-material';
import { useAuth } from '../context/AuthContext';
import { loginUser, loginStudent, getStudentOptions } from '../services/api';
import { StudentOptions } from '../types';

const MAX_STUDENT_IDENTIFIER = 99999999999999;
const JNV_BANGALORE_URBAN = 'JNV Bangalore Urban';

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
  const [selectedStudentId, setSelectedStudentId] = useState('');

  // Ekya School JP Nagar pilot students
  const EKYA_JP_NAGAR_STUDENTS = [
    "Aakarsh_Ekya_School_JP_Nagar_8_B_1",
    "Aanya_Ekya_School_JP_Nagar_8_B_2",
    "Abhigna_Ekya_School_JP_Nagar_8_B_3",
    "Achintya_Ekya_School_JP_Nagar_8_B_4",
    "Akshara_Ekya_School_JP_Nagar_8_B_5",
    "Alisha_Ekya_School_JP_Nagar_8_B_28",
    "Anika_Ekya_School_JP_Nagar_8_B_6",
    "Arnav_Ekya_School_JP_Nagar_8_B_7",
    "Rishith_Ekya_School_JP_Nagar_8_B_26",
    "Karthik_Ekya_School_JP_Nagar_8_B_10",
    "Kiara_Ekya_School_JP_Nagar_8_B_9",
    "Manyatha_Ekya_School_JP_Nagar_8_B_8",
    "Natasha_Ekya_School_JP_Nagar_8_B_11",
    "Nikhil_Ekya_School_JP_Nagar_8_B_12",
    "Preetham_Ekya_School_JP_Nagar_8_B_13",
    "Niharika_Ekya_School_JP_Nagar_8_B_14",
    "Rakshan_Ekya_School_JP_Nagar_8_B_15",
    "Sahasra_Ekya_School_JP_Nagar_8_B_16",
    "Samairra_Ekya_School_JP_Nagar_8_B_17",
    "Samanyu_Ekya_School_JP_Nagar_8_B_18",
    "Saraswatee_Ekya_School_JP_Nagar_8_B_27",
    "Shreegowri_Ekya_School_JP_Nagar_8_B_19",
    "Shreshta_Ekya_School_JP_Nagar_8_B_20",
    "Sihi_Ekya_School_JP_Nagar_8_B_21",
    "Siya_Ekya_School_JP_Nagar_8_B_22",
    "Swara_Ekya_School_JP_Nagar_8_B_23",
    "Karthikeya_Ekya_School_JP_Nagar_8_B_24",
    "Varnit_Ekya_School_JP_Nagar_8_B_25"
  ];

  const isEkyaJPNagar = school === 'Ekya School JP Nagar';
  const isJnvBangaloreUrban = school === JNV_BANGALORE_URBAN;
  const rollNumberFieldLabel = isJnvBangaloreUrban ? 'Student ID' : 'Roll Number';

  // Auto-set grade and section for Ekya JP Nagar
  useEffect(() => {
    if (isEkyaJPNagar) {
      setGrade(8);
      setSection('B');
    }
  }, [isEkyaJPNagar]);

  // Handle student selection for Ekya JP Nagar
  const handleStudentSelection = (studentId: string) => {
    setSelectedStudentId(studentId);
    if (studentId) {
      // Parse the student ID: {name}_Ekya_School_JP_Nagar_8_B_{roll_number}
      const parts = studentId.split('_');
      const name = parts[0];
      const rollNum = parts[parts.length - 1];
      setFirstName(name);
      setRollNumber(Number(rollNum));
    } else {
      setFirstName('');
      setRollNumber('');
    }
  };

  // Handle school change
  const handleSchoolChange = (schoolName: string) => {
    setSchool(schoolName);
    // Reset fields when changing schools
    if (schoolName !== 'Ekya School JP Nagar') {
      setSelectedStudentId('');
      setGrade('');
      setSection('');
      setRollNumber('');
      setFirstName('');
    }
  };

  // Debug mode detection from URL query params
  const searchParams = new URLSearchParams(location.search);
  const debugMode = searchParams.get('debug') === 'true';
  const tryMode = location.pathname === '/try' || searchParams.get('mode') === 'try';
  const useIdentifierLogin = debugMode || tryMode;
  const fieldClass = 'appearance-none relative block w-full rounded-xl border border-violet-200 bg-white px-3 py-3 text-base text-gray-900 shadow-sm focus:outline-none focus:ring-2 focus:ring-violet-200 focus:border-violet-400 sm:py-2 sm:text-sm disabled:cursor-not-allowed disabled:bg-violet-50';
  const labelClass = 'mb-1 block text-sm font-medium text-slate-700';
  const helpClass = 'mt-1 text-xs text-slate-500';

  const [studentOptions, setStudentOptions] = useState<StudentOptions | null>(null);
  const [studentOptionsLoading, setStudentOptionsLoading] = useState(false);
  const [studentOptionsError, setStudentOptionsError] = useState<string | null>(null);

  useEffect(() => {
    if (useIdentifierLogin) {
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
  }, [useIdentifierLogin]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      if (useIdentifierLogin) {
        // Identifier-based login for debug and try modes
        const response = await loginUser(identifier);
        if (response.success && response.user) {
          login(response.user);

          // Preserve query parameters during navigation
          const queryParams = new URLSearchParams(location.search);
          if (tryMode && !queryParams.has('mode')) {
            queryParams.set('mode', 'try');
          }
          const targetPath = queryParams.toString() ? `/chat?${queryParams.toString()}` : '/chat';
          navigate(targetPath);
        } else {
          setError(response.message || 'Login failed');
        }
      } else {
        // Student mode: use student login
        if (!school || grade === '' || !firstName) {
          setError('Please fill in all required fields');
          setIsLoading(false);
          return;
        }

        // For Ekya JP Nagar, validate student selection
        if (isEkyaJPNagar && !selectedStudentId) {
          setError('Please select your name from the dropdown');
          setIsLoading(false);
          return;
        }

        // For non-Ekya schools, validate roll number
        if (!isEkyaJPNagar && rollNumber === '') {
          setError(`Please enter your ${rollNumberFieldLabel.toLowerCase()}`);
          setIsLoading(false);
          return;
        }

        if (!isEkyaJPNagar && (Number(rollNumber) < 1 || Number(rollNumber) > MAX_STUDENT_IDENTIFIER)) {
          setError(`${rollNumberFieldLabel} must be between 1 and ${MAX_STUDENT_IDENTIFIER}`);
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
    <div className="main-gradient-bg min-h-screen flex items-center justify-center px-4 py-8 sm:px-6 sm:py-12 lg:px-8">
      <div className="w-full max-w-md space-y-6 rounded-3xl border border-violet-200 bg-white/95 p-6 shadow-sm sm:space-y-8 sm:p-8">
        <div>
          <div className="mx-auto mb-4 inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-violet-100 text-violet-700">
            <AutoAwesomeRounded />
          </div>
          <h2 className="text-center text-2xl font-extrabold text-gray-900 sm:text-3xl">
            Curiosity Coach
          </h2>
          <p className="mt-2 text-center text-sm text-violet-700">
            Sign in to start your learning journey
          </p>
        </div>

        <form className="mt-6 sm:mt-8 space-y-4 sm:space-y-6" onSubmit={handleSubmit}>
          {useIdentifierLogin ? (
            // Identifier-based login for debug and try modes
            <div>
              <label htmlFor="identifier" className="sr-only">User ID</label>
              <input
                id="identifier"
                name="identifier"
                type="text"
                autoComplete="off"
                required
                className={fieldClass}
                placeholder="User ID"
                value={identifier}
                onChange={(e) => setIdentifier(e.target.value)}
              />
              <p className={helpClass}>
                {debugMode ? 'Developer mode: Enter user ID for testing' : 'Enter user ID for testing'}
              </p>
            </div>
          ) : (
            // Student mode: Multiple fields
            <>
              {studentOptionsLoading && (
                <div className="text-center text-sm text-slate-500">
                  Loading school details...
                </div>
              )}
              {studentOptionsError && (
                <div className="text-center text-sm text-red-600">
                  {studentOptionsError}
                </div>
              )}
              <div>
                <label htmlFor="school" className={labelClass}>
                  School *
                </label>
                <select
                  id="school"
                  name="school"
                  required
                  className={fieldClass}
                  value={school}
                  onChange={(e) => handleSchoolChange(e.target.value)}
                  disabled={!studentOptions}
                >
                  <option value="">Select your school</option>
                  {studentOptions?.schools.map((s) => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
                <p className={helpClass}>Choose your school from the list</p>
              </div>

              {/* For Ekya JP Nagar - show name dropdown, hide other fields */}
              {isEkyaJPNagar ? (
                <>
                  <div>
                    <label htmlFor="studentName" className={labelClass}>
                      Select Your Name *
                    </label>
                    <select
                      id="studentName"
                      name="studentName"
                      required
                      className={fieldClass}
                      value={selectedStudentId}
                      onChange={(e) => handleStudentSelection(e.target.value)}
                    >
                      <option value="">Choose your name</option>
                      {EKYA_JP_NAGAR_STUDENTS.map((studentId) => {
                        const name = studentId.split('_')[0];
                        return (
                          <option key={studentId} value={studentId}>{name}</option>
                        );
                      })}
                    </select>
                    <p className={helpClass}>Grade 8, Section B</p>
                  </div>
                </>
              ) : (
                <>
                  <div>
                    <label htmlFor="grade" className={labelClass}>
                      Grade *
                    </label>
                    <select
                      id="grade"
                      name="grade"
                      required
                      className={fieldClass}
                      value={grade}
                      onChange={(e) => setGrade(Number(e.target.value))}
                      disabled={!studentOptions}
                    >
                      <option value="">Select your grade</option>
                      {studentOptions?.grades.map((g) => (
                        <option key={g} value={g}>Grade {g}</option>
                      ))}
                    </select>
                    <p className={helpClass}>Select your current grade (3 to 10)</p>
                  </div>

                  <div>
                    <label htmlFor="section" className={labelClass}>
                      Section (Optional)
                    </label>
                    <select
                      id="section"
                      name="section"
                      className={fieldClass}
                      value={section}
                      onChange={(e) => setSection(e.target.value)}
                      disabled={!studentOptions}
                    >
                      <option value="">No section / Not applicable</option>
                      {studentOptions?.sections.map((s) => (
                        <option key={s} value={s}>Section {s}</option>
                      ))}
                    </select>
                    <p className={helpClass}>Select your section if your school has sections (A, B, C, etc.)</p>
                  </div>

                  <div>
                    <label htmlFor="rollNumber" className={labelClass}>
                      {rollNumberFieldLabel} *
                    </label>
                    <input
                      id="rollNumber"
                      name="rollNumber"
                      type="number"
                      min="1"
                      max={MAX_STUDENT_IDENTIFIER}
                      step="1"
                      required
                      className={fieldClass}
                      placeholder={isJnvBangaloreUrban ? 'Enter your student ID' : 'Enter your roll number'}
                      value={rollNumber}
                      onChange={(e) => setRollNumber(e.target.value ? Number(e.target.value) : '')}
                    />
                    <p className={helpClass}>
                      {isJnvBangaloreUrban
                        ? 'Enter your numeric student ID (up to 14 digits)'
                        : 'Your roll number in your class'}
                    </p>
                  </div>

                  <div>
                    <label htmlFor="firstName" className={labelClass}>
                      First Name *
                    </label>
                    <input
                      id="firstName"
                      name="firstName"
                      type="text"
                      autoComplete="given-name"
                      required
                      className={fieldClass}
                      placeholder="Enter your first name"
                      value={firstName}
                      onChange={(e) => setFirstName(e.target.value)}
                    />
                    <p className={helpClass}>Enter your first name (e.g., Amit, Priya)</p>
                  </div>
                </>
              )}
            </>
          )}

          {error && (
            <div className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-center text-sm text-red-600">{error}</div>
          )}

          <div>
            <button
              type="submit"
              disabled={isLoading}
              className="group relative flex w-full justify-center rounded-xl border border-transparent bg-violet-500 px-4 py-3 text-base font-medium text-white hover:bg-violet-600 focus:outline-none focus:ring-2 focus:ring-violet-200 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 sm:py-2 sm:text-sm"
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
