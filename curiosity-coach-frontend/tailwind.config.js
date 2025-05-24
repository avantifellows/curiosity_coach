/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
    "./public/index.html"
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          light: '#4dabf5',
          DEFAULT: '#1976d2',
          dark: '#1565c0',
        },
        secondary: {
          light: '#ff4081',
          DEFAULT: '#f50057',
          dark: '#c51162',
        },
        gray: {
          lightest: '#f5f5f5',
          light: '#e0e0e0',
          DEFAULT: '#9e9e9e',
          dark: '#616161',
          darkest: '#212121',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      screens: {
        'xs': '475px',
        'touch': { 'raw': '(hover: none)' },
      },
      spacing: {
        'safe-area-inset-top': 'env(safe-area-inset-top)',
        'safe-area-inset-bottom': 'env(safe-area-inset-bottom)',
        'safe-area-inset-left': 'env(safe-area-inset-left)',
        'safe-area-inset-right': 'env(safe-area-inset-right)',
      },
      minHeight: {
        'touch-target': '44px',
      },
      minWidth: {
        'touch-target': '44px',
      },
    },
  },
  plugins: [],
} 