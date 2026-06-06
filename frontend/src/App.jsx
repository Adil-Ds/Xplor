/**
 * App.jsx
 * -------
 * Root component of the Xplor application.
 *
 * The entire app is wrapped inside <LocationPermission> which:
 *  1. Shows a permission prompt to the user
 *  2. Fetches live location once permission is granted
 *  3. Stores it in the `userLocation` variable (useLocation hook)
 *  4. Only then renders the rest of the app
 */

import LocationPermission from "./components/Auth/LocationPermission";

export default function App() {
  return (
    <LocationPermission>
      {/* ── Your app screens go here ── */}
      <MainApp />
    </LocationPermission>
  );
}

// ─── Placeholder main app (replace with your actual routes/screens) ───────────

function MainApp() {
  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <div style={styles.badge}>📍 Location Granted</div>
        <h1 style={styles.title}>Welcome to Xplor</h1>
        <p style={styles.subtitle}>
          Your live location has been fetched and stored successfully.
          The app is ready to go.
        </p>
        <LocationDebug />
      </div>
    </div>
  );
}

// ─── Debug panel — shows the stored userLocation variable ────────────────────

import { useLocation } from "./hooks/useLocation";

function LocationDebug() {
  const { userLocation, permissionStatus } = useLocation();

  return (
    <div style={styles.debug}>
      <p style={styles.debugTitle}>📦 Stored Variable: <code>userLocation</code></p>
      <pre style={styles.pre}>
        {JSON.stringify(userLocation, null, 2)}
      </pre>
      <p style={styles.status}>
        Status: <span style={styles.pill}>{permissionStatus}</span>
      </p>
    </div>
  );
}

// ─── Styles ───────────────────────────────────────────────────────────────────

const styles = {
  container: {
    minHeight       : "100vh",
    background      : "linear-gradient(135deg, #0f0c29, #302b63, #24243e)",
    display         : "flex",
    alignItems      : "center",
    justifyContent  : "center",
    fontFamily      : "'Inter', 'Segoe UI', sans-serif",
    padding         : "2rem",
  },
  card: {
    background      : "rgba(255,255,255,0.07)",
    border          : "1px solid rgba(255,255,255,0.15)",
    borderRadius    : "20px",
    padding         : "3rem 2.5rem",
    maxWidth        : "480px",
    width           : "100%",
    backdropFilter  : "blur(12px)",
    boxShadow       : "0 25px 60px rgba(0,0,0,0.4)",
    color           : "#fff",
    textAlign       : "center",
  },
  badge: {
    display         : "inline-block",
    background      : "rgba(134,239,172,0.15)",
    border          : "1px solid rgba(134,239,172,0.3)",
    color           : "#86efac",
    borderRadius    : "999px",
    padding         : "0.3rem 1rem",
    fontSize        : "0.8rem",
    fontWeight      : "600",
    marginBottom    : "1.2rem",
  },
  title: {
    fontSize        : "2rem",
    fontWeight      : "700",
    background      : "linear-gradient(90deg, #a78bfa, #60a5fa)",
    WebkitBackgroundClip : "text",
    WebkitTextFillColor  : "transparent",
    marginBottom    : "0.6rem",
  },
  subtitle: {
    color           : "rgba(255,255,255,0.6)",
    fontSize        : "0.95rem",
    lineHeight      : "1.6",
    marginBottom    : "2rem",
  },
  debug: {
    background      : "rgba(0,0,0,0.3)",
    border          : "1px solid rgba(255,255,255,0.1)",
    borderRadius    : "12px",
    padding         : "1.2rem",
    textAlign       : "left",
  },
  debugTitle: {
    fontSize        : "0.85rem",
    color           : "rgba(255,255,255,0.5)",
    marginBottom    : "0.6rem",
  },
  pre: {
    fontSize        : "0.82rem",
    color           : "#a78bfa",
    whiteSpace      : "pre-wrap",
    margin          : 0,
    lineHeight      : "1.7",
  },
  status: {
    marginTop       : "0.8rem",
    fontSize        : "0.82rem",
    color           : "rgba(255,255,255,0.45)",
  },
  pill: {
    background      : "rgba(96,165,250,0.2)",
    color           : "#60a5fa",
    borderRadius    : "999px",
    padding         : "0.15rem 0.6rem",
    fontSize        : "0.8rem",
  },
};
