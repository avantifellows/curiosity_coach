/**
 * Design System Constants
 * 
 * Centralized design tokens for consistent styling across the application.
 * These constants should be used instead of hard-coded values in components.
 */

// Color palette
export const colors = {
  primary: {
    50: '#e3f2fd',
    100: '#bbdefb',
    200: '#90caf9',
    300: '#64b5f6',
    400: '#42a5f5',
    500: '#2196f3',
    600: '#1e88e5',
    700: '#1976d2',
    800: '#1565c0',
    900: '#0d47a1',
    light: '#4dabf5',
    DEFAULT: '#1976d2',
    dark: '#1565c0',
  },
  secondary: {
    50: '#fce4ec',
    100: '#f8bbd9',
    200: '#f48fb1',
    300: '#f06292',
    400: '#ec407a',
    500: '#e91e63',
    600: '#d81b60',
    700: '#c2185b',
    800: '#ad1457',
    900: '#880e4f',
    light: '#ff4081',
    DEFAULT: '#f50057',
    dark: '#c51162',
  },
  gray: {
    50: '#fafafa',
    100: '#f5f5f5',
    200: '#eeeeee',
    300: '#e0e0e0',
    400: '#bdbdbd',
    500: '#9e9e9e',
    600: '#757575',
    700: '#616161',
    800: '#424242',
    900: '#212121',
    lightest: '#f5f5f5',
    light: '#e0e0e0',
    DEFAULT: '#9e9e9e',
    dark: '#616161',
    darkest: '#212121',
  },
  // Gradient definitions for consistent usage
  gradients: {
    primary: 'bg-gradient-to-r from-primary-500 to-primary-600',
    secondary: 'bg-gradient-to-r from-secondary-500 to-secondary-600',
    indigo: 'bg-gradient-to-r from-indigo-500 to-purple-500',
    blue: 'bg-gradient-to-r from-blue-500 to-indigo-600',
    purple: 'bg-gradient-to-r from-purple-500 to-pink-500',
    glass: 'bg-white bg-opacity-20 backdrop-blur-sm',
  },
} as const;

// Spacing scale
export const spacing = {
  xs: '0.25rem',   // 4px
  sm: '0.5rem',    // 8px
  md: '1rem',      // 16px
  lg: '1.5rem',    // 24px
  xl: '2rem',      // 32px
  '2xl': '3rem',   // 48px
  '3xl': '4rem',   // 64px
  '4xl': '6rem',   // 96px
  '5xl': '8rem',   // 128px
} as const;

// Border radius values
export const borderRadius = {
  none: '0',
  sm: '0.125rem',   // 2px
  md: '0.25rem',    // 4px
  lg: '0.5rem',     // 8px
  xl: '0.75rem',    // 12px
  '2xl': '1rem',    // 16px
  '3xl': '1.5rem',  // 24px
  full: '9999px',
} as const;

// Shadow definitions
export const shadows = {
  sm: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
  md: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
  lg: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
  xl: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
  '2xl': '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
  glass: '0 8px 32px 0 rgba(31, 38, 135, 0.37)',
} as const;

// Typography scale
export const typography = {
  fontFamily: {
    sans: ['Inter', 'system-ui', 'sans-serif'],
  },
  fontSize: {
    xs: '0.75rem',    // 12px
    sm: '0.875rem',   // 14px
    base: '1rem',     // 16px
    lg: '1.125rem',   // 18px
    xl: '1.25rem',    // 20px
    '2xl': '1.5rem',  // 24px
    '3xl': '1.875rem', // 30px
    '4xl': '2.25rem', // 36px
  },
  fontWeight: {
    light: '300',
    normal: '400',
    medium: '500',
    semibold: '600',
    bold: '700',
  },
  lineHeight: {
    tight: '1.25',
    normal: '1.5',
    relaxed: '1.75',
  },
} as const;

// Animation durations
export const animations = {
  duration: {
    fast: '150ms',
    normal: '200ms',
    slow: '300ms',
    slower: '500ms',
  },
  easing: {
    default: 'cubic-bezier(0.4, 0, 0.2, 1)',
    in: 'cubic-bezier(0.4, 0, 1, 1)',
    out: 'cubic-bezier(0, 0, 0.2, 1)',
    inOut: 'cubic-bezier(0.4, 0, 0.2, 1)',
  },
} as const;

// Breakpoints for responsive design
export const breakpoints = {
  xs: '475px',
  sm: '640px',
  md: '768px',
  lg: '1024px',
  xl: '1280px',
  '2xl': '1536px',
} as const;

// Z-index layers
export const zIndex = {
  hide: -1,
  auto: 'auto',
  base: 0,
  docked: 10,
  dropdown: 1000,
  sticky: 1020,
  banner: 1030,
  overlay: 1040,
  modal: 1050,
  popover: 1060,
  skipLink: 1070,
  toast: 1080,
  tooltip: 1090,
} as const;

// Common component styles
export const components = {
  button: {
    base: 'font-medium focus:outline-none focus:ring-2 focus:ring-offset-2 transition-all duration-200 touch-manipulation',
    sizes: {
      sm: 'px-3 py-2 text-sm rounded-lg min-h-touch-target',
      md: 'px-4 py-3 text-base rounded-xl min-h-touch-target',
      lg: 'px-6 py-4 text-lg rounded-2xl min-h-touch-target',
    },
    variants: {
      primary: 'bg-gradient-to-r from-primary-500 to-primary-600 text-white hover:from-primary-600 hover:to-primary-700 focus:ring-primary-500',
      secondary: 'bg-gradient-to-r from-secondary-500 to-secondary-600 text-white hover:from-secondary-600 hover:to-secondary-700 focus:ring-secondary-500',
      ghost: 'text-primary-600 hover:text-primary-800 hover:bg-primary-50 focus:ring-primary-500',
      glass: 'bg-white bg-opacity-20 backdrop-blur-sm text-white hover:bg-opacity-30 focus:ring-white focus:ring-opacity-50',
    },
  },
  input: {
    base: 'border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-colors',
    sizes: {
      sm: 'text-sm py-1.5',
      md: 'text-base py-2',
      lg: 'text-lg py-3',
    },
  },
  modal: {
    backdrop: 'fixed inset-0 bg-black bg-opacity-50 backdrop-blur-sm z-modal',
    content: 'bg-white rounded-2xl p-6 max-w-md w-full mx-4 shadow-2xl',
    mobile: 'fixed inset-0 z-modal overflow-y-auto pt-safe-area-inset-top pb-safe-area-inset-bottom pl-safe-area-inset-left pr-safe-area-inset-right',
  },
  chat: {
    bubble: {
      base: 'max-w-[85%] sm:max-w-[75%] p-3 rounded-lg break-words',
      user: 'bg-primary-dark text-white ml-auto',
      bot: 'bg-gray-lightest text-gray-darkest',
    },
  },
} as const;

// Mobile-specific constants
export const mobile = {
  minTouchTarget: '44px',
  safeAreaInsets: {
    top: 'env(safe-area-inset-top)',
    bottom: 'env(safe-area-inset-bottom)',
    left: 'env(safe-area-inset-left)',
    right: 'env(safe-area-inset-right)',
  },
  viewport: {
    height: '100dvh', // Dynamic viewport height
    fallbackHeight: '100vh',
  },
} as const;