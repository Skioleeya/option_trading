/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: {
          primary: 'var(--bg-primary)',
          secondary: '#111111',
          card: 'var(--bg-card)',
          border: 'var(--bg-border)',
        },
        market: {
          up: 'var(--market-up)',
          down: 'var(--market-down)',
          neutral: 'var(--market-neutral)',
        },
        wall: {
          call: 'var(--wall-call-bg)',
          put: 'var(--wall-put-bg)',
        },
        accent: {
          green: 'var(--accent-green)',
          red: 'var(--accent-red)',
          amber: 'var(--accent-amber)',
          purple: 'var(--accent-purple)',
          cyan: 'var(--accent-cyan)',
          blue: 'var(--accent-blue)',
        },
        text: {
          primary: 'var(--text-primary)',
          secondary: 'var(--text-secondary)',
          muted: 'var(--text-muted)',
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
