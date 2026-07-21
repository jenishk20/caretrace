// Minimal localStorage-backed session (staff + patient). Not a security boundary
// — just identity for attribution on a single local device.

const STAFF_KEY = "confide.staff";
const PATIENT_KEY = "confide.patient";

export const session = {
  staff: () => JSON.parse(localStorage.getItem(STAFF_KEY) || "null"),
  setStaff: (s) => localStorage.setItem(STAFF_KEY, JSON.stringify(s)),
  clearStaff: () => localStorage.removeItem(STAFF_KEY),

  patient: () => JSON.parse(localStorage.getItem(PATIENT_KEY) || "null"),
  setPatient: (p) => localStorage.setItem(PATIENT_KEY, JSON.stringify(p)),
  clearPatient: () => localStorage.removeItem(PATIENT_KEY),
};
