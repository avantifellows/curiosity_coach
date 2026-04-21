import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AutoAwesomeRounded } from '@mui/icons-material';
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
  const fieldClass = 'mt-1 block w-full rounded-xl border border-violet-200 bg-white px-3 py-3 text-base text-slate-900 shadow-sm focus:border-violet-400 focus:outline-none focus:ring-2 focus:ring-violet-200 sm:py-2 sm:text-sm disabled:cursor-not-allowed disabled:bg-violet-50';
  const labelClass = 'block text-sm font-medium text-slate-700';

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

    if (!school || !grade) {
      setError('Please select a school and grade.');
      return;
    }

    const gradeNumber = Number(grade);
    if (Number.isNaN(gradeNumber)) {
      setError('Invalid grade selection.');
      return;
    }

    const normalizedSection = section.trim().toUpperCase() || null;

    const trimmedSchool = school.trim();
    if (!trimmedSchool) {
      setError('Invalid school selection.');
      return;
    }

    setIsSubmitting(true);
    navigate('/teacher-dashboard', {
      state: { school: trimmedSchool, grade: gradeNumber, section: normalizedSection ?? undefined },
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
    <div className="main-gradient-bg min-h-screen flex items-center justify-center px-4 py-8">
      <div className="max-w-md w-full space-y-6 rounded-3xl border border-violet-200 bg-white/95 p-8 shadow-sm">
        <div>
          <div className="mx-auto mb-4 inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-violet-100 text-violet-700">
            <AutoAwesomeRounded />
          </div>
          <h2 className="text-center text-2xl font-bold text-gray-900">Teacher View</h2>
          <p className="mt-2 text-center text-sm text-violet-700">
            Enter your class details to continue.
          </p>
        </div>
        <form className="space-y-4" onSubmit={handleSubmit}>
          {studentOptionsLoading && (
            <p className="text-sm text-slate-500 text-center">Loading class options...</p>
          )}
          {studentOptionsError && (
            <p className="text-sm text-red-600 text-center">{studentOptionsError}</p>
          )}
          <div>
            <label htmlFor="school" className={labelClass}>
              School
            </label>
            <select
              id="school"
              name="school"
              className={fieldClass}
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
            <label htmlFor="grade" className={labelClass}>
              Grade
            </label>
            <select
              id="grade"
              name="grade"
              className={fieldClass}
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
              <option value="">No section</option>
              {studentOptions?.sections.map((s) => (
                <option key={s} value={s}>
                  Section {s}
                </option>
              ))}
            </select>
            <p className="mt-1 text-xs text-slate-500">
              Leave this blank if the student logged in without a section.
            </p>
          </div>
          {error && <p className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-600">{error}</p>}
          <button
            type="submit"
            className="w-full flex justify-center rounded-xl border border-transparent bg-violet-500 px-4 py-3 text-sm font-medium text-white shadow-sm hover:bg-violet-600 focus:outline-none focus:ring-2 focus:ring-violet-200 focus:ring-offset-2"
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
