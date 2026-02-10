/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#2563EB',
          foreground: '#FFFFFF',
        },
        secondary: {
          DEFAULT: '#F1F5F9',
          foreground: '#1E293B',
        },
        success: {
          DEFAULT: '#22C55E',
          light: '#DCFCE7',
          foreground: '#166534',
        },
        warning: {
          DEFAULT: '#F59E0B',
          light: '#FEF3C7',
          foreground: '#92400E',
        },
        error: {
          DEFAULT: '#EF4444',
          light: '#FEE2E2',
          foreground: '#DC2626',
        },
        sidebar: '#F8FAFC',
        card: '#FFFFFF',
        border: '#E2E8F0',
        text: {
          primary: '#1E293B',
          secondary: '#64748B',
          muted: '#94A3B8',
          'on-dark': '#FFFFFF',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        'md': '6px',
        'lg': '8px',
        'pill': '9999px',
      },
    },
  },
  plugins: [],
}
