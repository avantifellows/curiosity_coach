export interface TeacherClassContext {
  school?: string;
  grade?: number | string;
  section?: string | null;
}

const STORAGE_KEY = 'teacherClassContext';

export const saveTeacherClassContext = (context: TeacherClassContext) => {
  if (typeof window === 'undefined') {
    return;
  }

  const payload: TeacherClassContext = {
    school: context.school?.trim() || undefined,
    grade: context.grade,
    section: context.section ?? null,
  };

  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
};

export const getSavedTeacherClassContext = (): TeacherClassContext => {
  if (typeof window === 'undefined') {
    return {};
  }

  const raw = window.localStorage.getItem(STORAGE_KEY);
  if (!raw) {
    return {};
  }

  try {
    const parsed = JSON.parse(raw) as TeacherClassContext;
    return {
      school: parsed.school?.trim() || undefined,
      grade: parsed.grade,
      section: parsed.section ?? null,
    };
  } catch {
    return {};
  }
};

export const resolveTeacherClassContext = (
  state?: TeacherClassContext | null
): TeacherClassContext => {
  const hasStateContext = Boolean(state?.school && state?.grade !== undefined && state?.grade !== null);
  return hasStateContext ? { ...state, section: state?.section ?? null } : getSavedTeacherClassContext();
};
