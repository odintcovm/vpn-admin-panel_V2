/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: '#0b1020',
        panel: '#111a2e',
        border: '#24324f',
        muted: '#8ea0c8'
      },
      boxShadow: {
        soft: '0 8px 24px rgba(4,10,25,0.25)'
      }
    }
  },
  plugins: []
}
