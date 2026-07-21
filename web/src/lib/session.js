// Minimal localStorage-backed session (staff + patient). Not a security boundary
// — just identity for attribution on a single local device.

const STAFF_KEY = "medsignal.staff";
const PATIENT_KEY = "medsignal.patient";
const LEGACY_STAFF_KEY = "confide.staff";
const LEGACY_PATIENT_KEY = "confide.patient";

function get(key) {
  return JSON.parse(localStorage.getItem(key) || "null");
}

export const session = {
  staff: () => get(STAFF_KEY) || get(LEGACY_STAFF_KEY),
  setStaff: (s) => localStorage.setItem(STAFF_KEY, JSON.stringify(s)),
  clearStaff: () => { localStorage.removeItem(STAFF_KEY); localStorage.removeItem(LEGACY_STAFF_KEY); },

  patient: () => get(PATIENT_KEY) || get(LEGACY_PATIENT_KEY),
  setPatient: (p) => localStorage.setItem(PATIENT_KEY, JSON.stringify(p)),
  clearPatient: () => { localStorage.removeItem(PATIENT_KEY); localStorage.removeItem(LEGACY_PATIENT_KEY); },
};
