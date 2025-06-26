/** @type {import('tailwindcss').Config} */
const { colors, spacing, borderRadius, typography, breakpoints, zIndex, mobile } = require('./src/constants/design');

module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
    "./public/index.html"
  ],
  theme: {
    extend: {
      colors,
      fontFamily: typography.fontFamily,
      fontSize: typography.fontSize,
      fontWeight: typography.fontWeight,
      lineHeight: typography.lineHeight,
      spacing: {
        ...spacing,
        'safe-area-inset-top': mobile.safeAreaInsets.top,
        'safe-area-inset-bottom': mobile.safeAreaInsets.bottom,
        'safe-area-inset-left': mobile.safeAreaInsets.left,
        'safe-area-inset-right': mobile.safeAreaInsets.right,
      },
      borderRadius,
      screens: {
        ...breakpoints,
        'xs': breakpoints.xs,
        'touch': { 'raw': '(hover: none)' },
      },
      zIndex,
      minHeight: {
        'touch-target': mobile.minTouchTarget,
      },
      minWidth: {
        'touch-target': mobile.minTouchTarget,
      },
      backdropBlur: {
        xs: '2px',
        sm: '4px',
        md: '8px',
        lg: '12px',
        xl: '16px',
        '2xl': '24px',
        '3xl': '32px',
      },
    },
  },
  plugins: [],
} 