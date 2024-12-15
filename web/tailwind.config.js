/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      maxWidth: {
        'md': '1000px', // Changed to max width for md
      },
    },
  },
  plugins: [],
}
