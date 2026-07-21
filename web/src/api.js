// Thin fetch wrapper against the local FastAPI backend.

async function req(path, { method = "GET", body, form } = {}) {
  const opts = { method, headers: {} };
  if (form) {
    opts.body = form;
  } else if (body !== undefined) {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  }
  const res = await fetch(path, opts);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const j = await res.json();
      detail = j.detail || j.error || detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  status: () => req("/api/status"),
  gemmaLogs: (limit = 20) => req(`/api/model/logs?limit=${limit}`),

  // auth
  staffLogin: (username, password) =>
    req("/api/auth/staff/login", { method: "POST", body: { username, password } }),
  staffRegister: (username, password, name) =>
    req("/api/auth/staff/register", { method: "POST", body: { username, password, name } }),
  patientLogin: (username, password) =>
    req("/api/auth/patient/login", { method: "POST", body: { username, password } }),

  // patients
  listPatients: (status) =>
    req(`/api/patients${status ? `?status=${status}` : ""}`),
  createPatient: (data) => req("/api/patients", { method: "POST", body: data }),
  getPatient: (id) => req(`/api/patients/${id}`),
  dischargePatient: (id) => req(`/api/patients/${id}/discharge`, { method: "POST" }),

  // graph + guardian
  getGraph: (id) => req(`/api/patients/${id}/graph`),
  addNode: (id, node) => req(`/api/patients/${id}/nodes`, { method: "POST", body: node }),
  completeNode: (nodeId) => req(`/api/nodes/${nodeId}/complete`, { method: "POST" }),
  listAlerts: (id, status) =>
    req(`/api/patients/${id}/alerts${status ? `?status=${status}` : ""}`),
  updateAlert: (alertId, status) =>
    req(`/api/alerts/${alertId}`, { method: "PUT", body: { status } }),
  guardianSweep: (id) => req(`/api/patients/${id}/guardian/sweep`, { method: "POST" }),

  // scribe
  scribeCapture: (data) => req("/api/scribe/capture", { method: "POST", body: data }),
  scribeEncounters: (id) => req(`/api/scribe/encounters?patient_id=${id}`),
  transcribe: (blob) => {
    const form = new FormData();
    form.append("audio", blob, "audio.webm");
    return req("/api/voice/transcribe", { method: "POST", form });
  },

  // dynamic workflow agent
  runAgent: (data) => req("/api/agent/run", { method: "POST", body: data }),
  uploadAgentImage: (file) => {
    const form = new FormData();
    form.append("image", file, file.name || "capture.png");
    return req("/api/agent/upload", { method: "POST", form });
  },
  approveAgent: (data) => req("/api/agent/approve", { method: "POST", body: data }),
  agentTrace: (encounterId) => req(`/api/agent/runs/${encounterId}/trace`),
  agentRuns: (patientId, limit = 3) => req(`/api/patients/${patientId}/agent-runs?limit=${limit}`),
  patientRoi: (patientId) => req(`/api/patients/${patientId}/roi`),

  // consent
  consentText: (data) => req("/api/consent/forms/text", { method: "POST", body: data }),
  consentImage: (patientId, staffId, file) => {
    const form = new FormData();
    form.append("patient_id", patientId);
    if (staffId) form.append("staff_id", staffId);
    form.append("image", file);
    return req("/api/consent/forms", { method: "POST", form });
  },
  consentList: (id) => req(`/api/consent/forms?patient_id=${id}`),
  consentAsk: (docId, patientId, question) =>
    req(`/api/consent/forms/${docId}/questions`, { method: "POST", body: { patient_id: patientId, question } }),
  consentQuestions: (docId, patientId) =>
    req(`/api/consent/forms/${docId}/questions?patient_id=${patientId}`),

  // discharge
  dischargeText: (data) => req("/api/discharge/documents/text", { method: "POST", body: data }),
  dischargeImage: (patientId, staffId, file) => {
    const form = new FormData();
    form.append("patient_id", patientId);
    if (staffId) form.append("staff_id", staffId);
    form.append("image", file);
    return req("/api/discharge/documents", { method: "POST", form });
  },
  dischargeList: (id) => req(`/api/discharge/documents?patient_id=${id}`),
  dischargeAsk: (docId, patientId, question) =>
    req(`/api/discharge/documents/${docId}/questions`, { method: "POST", body: { patient_id: patientId, question } }),

  // prescription (document upload → portal record + meds into the graph)
  prescriptionText: (data) => req("/api/prescription/documents/text", { method: "POST", body: data }),
  prescriptionImage: (patientId, staffId, file) => {
    const form = new FormData();
    form.append("patient_id", patientId);
    if (staffId) form.append("staff_id", staffId);
    form.append("image", file);
    return req("/api/prescription/documents", { method: "POST", form });
  },
  prescriptionList: (id) => req(`/api/prescription/documents?patient_id=${id}`),

  // memory
  askRoom: (id, question, askedBy = "staff") =>
    req("/api/memory/ask", { method: "POST", body: { patient_id: id, question, asked_by: askedBy } }),
  catchMeUp: (id) => req(`/api/memory/catch-me-up/${id}`, { method: "POST" }),

  // handoff
  generateHandoff: (id, staffId) =>
    req("/api/handoff", { method: "POST", body: { patient_id: id, staff_id: staffId } }),
  handoffHistory: (id) => req(`/api/handoff?patient_id=${id}`),

  // orientation
  orient: (id, staffId) =>
    req(`/api/orientation/${id}/generate`, { method: "POST", body: { staff_id: staffId } }),

  // reminders
  reminders: (id, status) =>
    req(`/api/patients/${id}/reminders${status ? `?status=${status}` : ""}`),
  addReminder: (id, data) => req(`/api/patients/${id}/reminders`, { method: "POST", body: data }),
  updateReminder: (rid, status) => req(`/api/reminders/${rid}`, { method: "PUT", body: { status } }),

  // patient-facing
  patientChat: (id, message) =>
    req("/api/patient/chat", { method: "POST", body: { patient_id: id, message } }),
  patientDebrief: (id) => req(`/api/patient/debrief/${id}`, { method: "POST" }),
  patientHistory: (id) => req(`/api/patient/history?patient_id=${id}`),
  patientReminders: (id) => req(`/api/patient/reminders?patient_id=${id}`),
};
