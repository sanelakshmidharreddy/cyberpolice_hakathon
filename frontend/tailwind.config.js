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
        forensic: {
          dark: '#0a0d14',
          card: '#111622',
          border: '#1e2638',
          accent: '#00f2fe',
          authentic: '#10b981',
          suspicious: '#f59e0b',
          tampered: '#ef4444',
          inconclusive: '#64748b'
        }
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
      }
    },
  },
  plugins: [],
}
