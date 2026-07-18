import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api } from "../api";

// No server-side session token — see SPEC.md's auth decisions. Staff identity and the
// active patient are held here and persisted to localStorage so a refresh doesn't log out.
const AppContext = createContext(null);

const STAFF_KEY = "do_staff";
const PATIENT_ID_KEY = "do_patient_id";

export function AppProvider({ children }) {
  const [staff, setStaffState] = useState(() => {
    const raw = localStorage.getItem(STAFF_KEY);
    return raw ? JSON.parse(raw) : null;
  });
  const [patientId, setPatientIdState] = useState(() => {
    const raw = localStorage.getItem(PATIENT_ID_KEY);
    return raw ? Number(raw) : null;
  });
  const [patient, setPatient] = useState(null);

  useEffect(() => {
    if (!patientId) {
      setPatient(null);
      return;
    }
    let cancelled = false;
    api.getPatient(patientId).then(
      (p) => !cancelled && setPatient(p),
      () => !cancelled && setPatient(null)
    );
    return () => {
      cancelled = true;
    };
  }, [patientId]);

  const login = useCallback((staffInfo) => {
    localStorage.setItem(STAFF_KEY, JSON.stringify(staffInfo));
    setStaffState(staffInfo);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(STAFF_KEY);
    localStorage.removeItem(PATIENT_ID_KEY);
    setStaffState(null);
    setPatientIdState(null);
    setPatient(null);
  }, []);

  const selectPatient = useCallback((id) => {
    localStorage.setItem(PATIENT_ID_KEY, String(id));
    setPatientIdState(id);
  }, []);

  const clearPatient = useCallback(() => {
    localStorage.removeItem(PATIENT_ID_KEY);
    setPatientIdState(null);
    setPatient(null);
  }, []);

  const refreshPatient = useCallback(() => {
    if (patientId) api.getPatient(patientId).then(setPatient);
  }, [patientId]);

  return (
    <AppContext.Provider
      value={{ staff, login, logout, patientId, patient, selectPatient, clearPatient, refreshPatient }}
    >
      {children}
    </AppContext.Provider>
  );
}

export function useApp() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error("useApp must be used within AppProvider");
  return ctx;
}
