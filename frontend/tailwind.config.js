/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js}'],
  theme: {
    extend: {
      colors: {
        primary: '#DDFCAD',
        secondary: '#C8E087',
        sage: '#95A472',
        olive: '#82846D'
      },
      boxShadow: {
        soft: '0 20px 60px rgba(130, 132, 109, 0.18)'
      }
    }
  },
  plugins: []
}
