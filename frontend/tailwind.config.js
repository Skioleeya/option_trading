/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: {
          primary: '#0a0a0a',
          secondary: '#111111',
          card: '#161616',
          border: '#222222',
        },
        accent: {
          green: '#00d68f',
          red: '#ff4d6d',
          amber: '#f59e0b',
          blue: '#3b82f6',
          purple: '#a855f7',
          cyan: '#06b6d4',
        },
        text: {
          primary: '#e4e4e7',
          secondary: '#71717a',
          muted: '#3f3f46',
        }
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'Courier New', 'monospace'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      fontSize: {
        '2xs': '0.625rem',
        xs: '0.7rem',
        sm: '0.8rem',
      },
    },
  },
  plugins: [],
}
