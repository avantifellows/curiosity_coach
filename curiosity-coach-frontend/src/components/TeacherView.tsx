import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { StudentOptions } from '../types';
import { getStudentOptions } from '../services/api';

const TeacherView: React.FC = () => {
  const [school, setSchool] = useState('');
  const [grade, setGrade] = useState('');
  const [section, setSection] = useState('');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const navigate = useNavigate();
  const [studentOptions, setStudentOptions] = useState<StudentOptions | null>(null);
  const [studentOptionsLoading, setStudentOptionsLoading] = useState(false);
  const [studentOptionsError, setStudentOptionsError] = useState<string | null>(null);

  useEffect(() => {
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
        console.error('Failed to fetch student options for teacher view:', err);
        if (isMounted) {
          setStudentOptionsError('Failed to load class options. Please refresh the page.');
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
  }, []);

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    setError('');

    if (!studentOptions) {
      setError('Class options are still loading. Please wait a moment.');
      return;
    }

    if (!school || !grade || !section) {
      setError('Please fill in all the fields.');
      return;
    }

    const gradeNumber = Number(grade);
    if (Number.isNaN(gradeNumber)) {
      setError('Invalid grade selection.');
      return;
    }

    const normalizedSection = section.trim().toUpperCase();
    if (!normalizedSection) {
      setError('Section cannot be empty.');
      return;
    }

    const trimmedSchool = school.trim();
    if (!trimmedSchool) {
      setError('Invalid school selection.');
      return;
    }

    setIsSubmitting(true);
    navigate('/teacher-dashboard', {
      state: { school: trimmedSchool, grade: gradeNumber, section: normalizedSection },
    });
    setIsSubmitting(false);
  };

  const handleSchoolChange = (value: string) => {
    setSchool(value);
    setGrade('');
    setSection('');
  };

  const handleGradeChange = (value: string) => {
    setGrade(value);
    setSection('');
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-8 px-4">
      <div className="max-w-md w-full space-y-6 bg-white p-8 rounded-lg shadow">
        <div>
          <h2 className="text-center text-2xl font-bold text-gray-900">Teacher View</h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            Enter your class details to continue.
          </p>
        </div>
        <form className="space-y-4" onSubmit={handleSubmit}>
          {studentOptionsLoading && (
            <p className="text-sm text-gray-500 text-center">Loading class options...</p>
          )}
          {studentOptionsError && (
            <p className="text-sm text-red-600 text-center">{studentOptionsError}</p>
          )}
          <div>
            <label htmlFor="school" className="block text-sm font-medium text-gray-700">
              School
            </label>
            <select
              id="school"
              name="school"
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
              value={school}
              onChange={(e) => handleSchoolChange(e.target.value)}
              disabled={!studentOptions}
            >
              <option value="">Select a school</option>
              {studentOptions?.schools.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="grade" className="block text-sm font-medium text-gray-700">
              Grade
            </label>
            <select
              id="grade"
              name="grade"
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
              value={grade}
              onChange={(e) => handleGradeChange(e.target.value)}
              disabled={!studentOptions}
            >
              <option value="">Select a grade</option>
              {studentOptions?.grades.map((g) => (
                <option key={g} value={g}>
                  Grade {g}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="section" className="block text-sm font-medium text-gray-700">
              Section
            </label>
            <select
              id="section"
              name="section"
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
              value={section}
              onChange={(e) => setSection(e.target.value)}
              disabled={!studentOptions}
            >
              <option value="">Select a section</option>
              {studentOptions?.sections.map((s) => (
                <option key={s} value={s}>
                  Section {s}
                </option>
              ))}
            </select>
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <button
            type="submit"
            className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
            disabled={isSubmitting || !studentOptions}
          >
            {isSubmitting ? 'Redirecting...' : 'Continue'}
          </button>
        </form>
      </div>
    </div>
  );
};

export default TeacherView;
