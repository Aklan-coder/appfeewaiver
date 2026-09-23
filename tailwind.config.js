/** Tailwind build config (production). Keep colours in sync with static/js/tailwind-cdn-config.js */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./*/templates/**/*.html",
    "./*/*.py",
    "./*/templatetags/*.py",
    "./static/js/**/*.js",
  ],
  theme: {
    extend: {
      colors: {
        navy: { 950: "#060f1f", 900: "#0a172d", 800: "#13233f", 700: "#1e3354", 600: "#334766" },
        brand: {
          50: "#ecfdf5", 100: "#d1fae5", 200: "#a7f3d0", 300: "#6ee7b7", 400: "#34d399",
          500: "#13a77a", 600: "#0e8c66", 700: "#0b7152", 800: "#0a5a42", 900: "#084a37",
        },
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "-apple-system", "Segoe UI", "Roboto", "sans-serif"],
        display: ["Plus Jakarta Sans", "Inter", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      maxWidth: { site: "96rem" },
    },
  },
  plugins: [],
};
