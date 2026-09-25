/* Development only: configuration for the Tailwind Play CDN. Mirrors tailwind.config.js */
window.tailwind = window.tailwind || {};
tailwind.config = {
  theme: {
    extend: {
      colors: {
        navy: { 950: "#061426", 900: "#0a1a33", 800: "#11294a", 700: "#1b3a60", 600: "#334766" },
        brand: {
          50: "#ecfdf5", 100: "#d1fae5", 200: "#a7f3d0", 300: "#6ee7b7", 400: "#22d3a0",
          500: "#13a77a", 600: "#0b8458", 700: "#09704b", 800: "#075a3d", 900: "#064a33",
        },
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "-apple-system", "Segoe UI", "Roboto", "sans-serif"],
        display: ["Plus Jakarta Sans", "Inter", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      maxWidth: { site: "86rem" },
    },
  },
};
