/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // CricketIQ Brand Design Tokens
        brand: {
          50: '#f7fee7',
          100: '#ecfccb',
          300: '#bef264',
          400: '#94ee58',
          500: '#7fea35', // Primary CricketIQ Lime Green
          600: '#68c827',
          700: '#4f9b1c',
        },
        // Secondary Telemetry Accent
        cyan: {
          400: '#22d3ee',
          500: '#00f0ff', // High-tech telemetry cyan
          600: '#0891b2',
        },
        // Dark theme surfaces
        navy: {
          950: '#050505', // Primary Canvas Background
          900: '#111315', // Secondary Background / Panels
          850: '#181b1d', // Cards & Surface Containers
          800: '#303438', // Subtle Borders & Dividers
          750: '#3a3f44', // Active / Selected States
          700: '#42474c', // Muted Borders & Badges
        },
        cricket: {
          dark: '#050505',
          surface: '#181b1d',
          lime: '#7fea35',
          cyan: '#00f0ff',
          border: '#303438',
          amber: '#e5a118',
          red: '#ef4444',
          sky: '#38bdf8',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        display: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      animation: {
        'pulse-subtle': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      }
    },
  },
  plugins: [],
}
