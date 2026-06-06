/**
 * useLocation.js
 * --------------
 * Custom React hook for fetching the user's live geographic location.
 *
 * HOW IT WORKS:
 *  1. When called, it prompts the browser's permission dialog.
 *  2. If the user GRANTS permission  → live coordinates are fetched and
 *     stored in the `userLocation` state variable.
 *  3. If the user DENIES permission  → `permissionDenied` is set to true
 *     and the app can handle the blocked flow.
 *
 * WHERE IS THE VARIABLE STORED?
 *  The location data lives in React component state via `useState`.
 *  Variable name : `userLocation`
 *  State is held in memory (RAM) for the duration of the browser session.
 *  It is also mirrored to `sessionStorage` under the key "xplor_user_location"
 *  so it survives page refreshes within the same tab.
 */

import { useState, useEffect, useCallback } from "react";

// ─── Constants ───────────────────────────────────────────────────────────────

/** Key used to persist the location in sessionStorage */
const SESSION_KEY = "xplor_user_location";

/** Geolocation options */
const GEO_OPTIONS = {
  enableHighAccuracy: true,   // Use GPS if available (more accurate)
  timeout: 10_000,            // Give up after 10 seconds
  maximumAge: 0,              // Never use a cached position — always live
};

// ─── Hook ────────────────────────────────────────────────────────────────────

/**
 * useLocation
 *
 * @returns {{
 *   userLocation: { latitude: number, longitude: number, accuracy: number, timestamp: number } | null,
 *   permissionStatus: "idle" | "requesting" | "granted" | "denied" | "unavailable",
 *   permissionDenied: boolean,
 *   isLoading: boolean,
 *   error: string | null,
 *   requestLocation: () => void,
 * }}
 */
export function useLocation() {
  // ── MAIN VARIABLE: userLocation ──────────────────────────────────────────
  // This is where the live location is stored.
  // Shape: { latitude, longitude, accuracy, timestamp }
  // Initially read from sessionStorage (if a previous fetch exists in this tab).
  const [userLocation, setUserLocation] = useState(() => {
    try {
      const cached = sessionStorage.getItem(SESSION_KEY);
      return cached ? JSON.parse(cached) : null;
    } catch {
      return null;
    }
  });

  const [permissionStatus, setPermissionStatus] = useState("idle");
  const [isLoading, setIsLoading]               = useState(false);
  const [error, setError]                        = useState(null);

  // ── Success handler ───────────────────────────────────────────────────────
  const onSuccess = useCallback((position) => {
    // Extract the coordinates from the browser's GeolocationPosition object
    const locationData = {
      latitude  : position.coords.latitude,
      longitude : position.coords.longitude,
      accuracy  : position.coords.accuracy,   // metres
      timestamp : position.timestamp,          // Unix ms
    };

    // 1️⃣  Store in React state  (primary storage — in memory)
    setUserLocation(locationData);

    // 2️⃣  Mirror to sessionStorage  (survives page refresh, cleared on tab close)
    try {
      sessionStorage.setItem(SESSION_KEY, JSON.stringify(locationData));
    } catch {
      // sessionStorage write failed — non-critical, ignore
    }

    setPermissionStatus("granted");
    setIsLoading(false);
    setError(null);
  }, []);

  // ── Error handler ─────────────────────────────────────────────────────────
  const onError = useCallback((err) => {
    setIsLoading(false);

    switch (err.code) {
      case err.PERMISSION_DENIED:
        setPermissionStatus("denied");
        setError("Location permission was denied. Please allow access to continue.");
        break;
      case err.POSITION_UNAVAILABLE:
        setPermissionStatus("unavailable");
        setError("Location information is unavailable on this device.");
        break;
      case err.TIMEOUT:
        setPermissionStatus("idle");
        setError("Location request timed out. Please try again.");
        break;
      default:
        setPermissionStatus("idle");
        setError("An unknown error occurred while fetching location.");
    }
  }, []);

  // ── Public trigger: call this to prompt the permission dialog ─────────────
  const requestLocation = useCallback(() => {
    // Guard: browser support check
    if (!navigator.geolocation) {
      setPermissionStatus("unavailable");
      setError("Geolocation is not supported by your browser.");
      return;
    }

    setIsLoading(true);
    setPermissionStatus("requesting");
    setError(null);

    // This call triggers the browser's permission popup
    navigator.geolocation.getCurrentPosition(onSuccess, onError, GEO_OPTIONS);
  }, [onSuccess, onError]);

  // ── Auto-request on mount ─────────────────────────────────────────────────
  // If no cached location exists, immediately ask for permission when the
  // hook is first used. Comment this block out to make it manual-only.
  useEffect(() => {
    if (!userLocation) {
      requestLocation();
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Return values ─────────────────────────────────────────────────────────
  return {
    userLocation,                                    // ← THE MAIN VARIABLE
    permissionStatus,                                // "idle" | "requesting" | "granted" | "denied" | "unavailable"
    permissionDenied : permissionStatus === "denied",
    isLoading,
    error,
    requestLocation,                                 // call manually to re-trigger
  };
}
