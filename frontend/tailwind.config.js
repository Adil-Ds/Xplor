/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        "primary-fixed": "#e9ddff",
        "on-error": "#690005",
        "surface-dim": "#141218",
        "secondary-fixed-dim": "#cdc0e9",
        "background": "#141218",
        "on-tertiary-container": "#503d00",
        "on-primary": "#381e72",
        "on-tertiary-fixed": "#241a00",
        "on-secondary": "#342b4b",
        "surface-container-highest": "#36343a",
        "error-container": "#93000a",
        "inverse-surface": "#e6e0e9",
        "surface": "#141218",
        "on-secondary-fixed-variant": "#4b4263",
        "surface-container": "#211f24",
        "secondary-fixed": "#e9ddff",
        "on-primary-fixed-variant": "#4f378a",
        "inverse-on-surface": "#322f35",
        "tertiary-fixed": "#ffdf93",
        "surface-container-lowest": "#0f0d13",
        "outline": "#948e9c",
        "surface-variant": "#36343a",
        "surface-container-low": "#1d1b20",
        "on-tertiary": "#3e2e00",
        "primary-container": "#6750a4",
        "on-secondary-fixed": "#1f1635",
        "secondary-container": "#4d4465",
        "on-surface": "#e6e0e9",
        "inverse-primary": "#6750a4",
        "on-primary-container": "#e0d2ff",
        "primary-fixed-dim": "#cfbcff",
        "on-background": "#e6e0e9",
        "outline-variant": "#494551",
        "error": "#ffb4ab",
        "on-error-container": "#ffdad6",
        "on-primary-fixed": "#22005d",
        "surface-tint": "#cfbcff",
        "primary": "#cfbcff",
        "surface-bright": "#3b383e",
        "on-secondary-container": "#bfb2da",
        "on-tertiary-fixed-variant": "#594400",
        "on-surface-variant": "#cbc4d2",
        "surface-container-high": "#2b292f",
        "tertiary-fixed-dim": "#e7c365",
        "secondary": "#cdc0e9",
        "tertiary": "#e7c365",
        "tertiary-container": "#c9a74d"
      },
      borderRadius: {
        "DEFAULT": "0.25rem",
        "lg": "0.5rem",
        "xl": "0.75rem",
        "2xl": "1rem",
        "full": "9999px"
      },
      spacing: {
        "gutter": "24px",
        "margin": "32px",
        "container-max": "1280px",
        "unit": "4px"
      },
      fontFamily: {
        "data-tabular": ["JetBrains Mono", "monospace"],
        "label-caps": ["Geist", "sans-serif"],
        "headline-md": ["Geist", "sans-serif"],
        "body-base": ["Geist", "sans-serif"],
        "display-lg": ["Geist", "sans-serif"],
        "sans": ["Geist", "Inter", "sans-serif"]
      },
      fontSize: {
        "data-tabular": ["14px", { lineHeight: "1.5", letterSpacing: "0em", fontWeight: "400" }],
        "label-caps": ["12px", { lineHeight: "1", letterSpacing: "0.05em", fontWeight: "600" }],
        "headline-md": ["24px", { lineHeight: "1.2", letterSpacing: "-0.02em", fontWeight: "600" }],
        "body-base": ["16px", { lineHeight: "1.6", letterSpacing: "-0.01em", fontWeight: "400" }],
        "display-lg": ["48px", { lineHeight: "1.1", letterSpacing: "-0.04em", fontWeight: "600" }]
      }
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/container-queries')
  ],
}
