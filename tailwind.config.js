/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./main/templates/**/*.html",
    "./main/**/*.py",
    "./carmarket/templates/**/*.html",
  ],
  theme: {
    extend: {},
  },
  plugins: [require("daisyui")],
  daisyui: {
    themes: ["light", "dark", "cupcake"],
  },
}