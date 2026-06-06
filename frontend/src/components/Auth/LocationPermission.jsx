/**
 * LocationPermission.jsx
 * ----------------------
 * A full-screen permission gate shown to the user before the app loads.
 * It uses the `useLocation` hook internally.
 *
 * USAGE:
 *   Wrap your entire app with this component so location is fetched once
 *   at startup before any other screen renders.
 *
 *   <LocationPermission>
 *     <App />
 *   </LocationPermission>
 *
 * The resolved `userLocation` variable is available via:
 *   1. The `useLocation()` hook — anywhere in the component tree
 *   2. The `window.__XPLOR_LOCATION__` global (set here for easy access)
 *   3. sessionStorage under key "xplor_user_location"
 */

import { useEffect } from "react";
import { useLocation } from "../../hooks/useLocation";

// ─── Inline styles (no external CSS dependency) ───────────────────────────────

const styles = {
  overlay: {
    position        : "fixed",
    inset           : 0,
    background      : "linear-gradient(135deg, #0f0c29, #302b63, #24243e)",
    display         : "flex",
    flexDirection   : "column",
    alignItems      : "center",
    justifyContent  : "center",
    zIndex          : 9999,
    fontFamily      : "'Inter', 'Segoe UI', sans-serif",
    color           : "#ffffff",
    padding         : "2rem",
    textAlign       : "center",
  },
  card: {
    background      : "rgba(255,255,255,0.07)",
    border          : "1px solid rgba(255,255,255,0.15)",
    borderRadius    : "20px",
    padding         : "3rem 2.5rem",
    maxWidth        : "440px",
    width           : "100%",
    backdropFilter  : "blur(12px)",
    boxShadow       : "0 25px 60px rgba(0,0,0,0.4)",
  },
  icon: {
    fontSize        : "3.5rem",
    marginBottom    : "1rem",
  },
  title: {
    fontSize        : "1.6rem",
    fontWeight      : "700",
    marginBottom    : "0.6rem",
    background      : "linear-gradient(90deg, #a78bfa, #60a5fa)",
    WebkitBackgroundClip : "text",
    WebkitTextFillColor  : "transparent",
  },
  subtitle: {
    fontSize        : "0.95rem",
    color           : "rgba(255,255,255,0.65)",
    lineHeight      : "1.6",
    marginBottom    : "2rem",
  },
  btn: {
    width           : "100%",
    padding         : "0.9rem 1.5rem",
    borderRadius    : "12px",
    border          : "none",
    background      : "linear-gradient(135deg, #7c3aed, #3b82f6)",
    color           : "#fff",
    fontSize        : "1rem",
    fontWeight      : "600",
    cursor          : "pointer",
    letterSpacing   : "0.02em",
    transition      : "opacity 0.2s",
  },
  btnLoading: {
    opacity         : 0.6,
    cursor          : "not-allowed",
  },
  error: {
    marginTop       : "1.2rem",
    padding         : "0.8rem 1rem",
    background      : "rgba(239,68,68,0.15)",
    border          : "1px solid rgba(239,68,68,0.35)",
    borderRadius    : "10px",
    fontSize        : "0.875rem",
    color           : "#fca5a5",
  },
  granted: {
    fontSize        : "0.8rem",
    color           : "rgba(255,255,255,0.4)",
    marginTop       : "1rem",
  },
};

// ─── Component ────────────────────────────────────────────────────────────────

export default function LocationPermission({ children }) {
  const {
    userLocation,       // ← THE VARIABLE — { latitude, longitude, accuracy, timestamp }
    permissionStatus,
    permissionDenied,
    isLoading,
    error,
    requestLocation,
  } = useLocation();

  // ── Expose userLocation globally so any non-React code can access it ──────
  useEffect(() => {
    if (userLocation) {
      window.__XPLOR_LOCATION__ = userLocation;
      console.info("[Xplor] Live location stored:", userLocation);
    }
  }, [userLocation]);

  // ── If location is already granted → render the actual app ───────────────
  if (permissionStatus === "granted" && userLocation) {
    return children;
  }

  // ── Full-screen permission gate ───────────────────────────────────────────
  return (
    <div style={styles.overlay}>
      <div style={styles.card}>

        {/* Icon */}
        <div style={styles.icon}>
          {isLoading ? "⏳" : permissionDenied ? "🚫" : "📍"}
        </div>

        {/* Title */}
        <div style={styles.title}>
          {isLoading
            ? "Detecting your location…"
            : permissionDenied
            ? "Location Access Required"
            : "Allow Location Access"}
        </div>

        {/* Subtitle */}
        <p style={styles.subtitle}>
          {permissionDenied
            ? "Xplor requires your location to work. Please reset browser permissions and try again."
            : "Xplor needs your live location to show personalised, nearby content. Your location is never shared with third parties."}
        </p>

        {/* Action button */}
        {!permissionDenied && (
          <button
            id="xplor-request-location-btn"
            style={{
              ...styles.btn,
              ...(isLoading ? styles.btnLoading : {}),
            }}
            onClick={requestLocation}
            disabled={isLoading}
          >
            {isLoading ? "Waiting for permission…" : "📍  Allow Location"}
          </button>
        )}

        {/* Error message */}
        {error && <div style={styles.error}>⚠️ {error}</div>}

        {/* Debug hint (remove in production) */}
        {permissionStatus === "granted" && (
          <p style={styles.granted}>✅ Location acquired — loading app…</p>
        )}
      </div>
    </div>
  );
}
