import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { useApp } from "../context/AppContext";

export default function PatientPicker() {
  const { staff, selectPatient } = useApp();
  const navigate = useNavigate();

  const [patients, setPatients] = useState([]);
  const [search, setSearch] = useState("");
  const searchTimer = useRef(null);

  const [name, setName] = useState("");
  const [mrn, setMrn] = useState("");
  const [room, setRoom] = useState("");
  const [lang, setLang] = useState("en");
  const [allergies, setAllergies] = useState("");
  const [admitError, setAdmitError] = useState("");

  async function loadPatients(q) {
    const result = await api.listPatients({ status: "admitted", search: q });
    setPatients(result);
  }

  useEffect(() => {
    loadPatients("");
  }, []);

  function onSearchChange(value) {
    setSearch(value);
    clearTimeout(searchTimer.current);
    searchTimer.current = setTimeout(() => loadPatients(value), 250);
  }

  function pick(id) {
    selectPatient(id);
    navigate("/dashboard");
  }

  async function admit() {
    setAdmitError("");
    if (!name.trim()) {
      setAdmitError("Name is required.");
      return;
    }
    try {
      const patient = await api.createPatient({
        name: name.trim(),
        staff_id: staff.id,
        mrn: mrn.trim() || null,
        room: room.trim() || null,
        primary_language: lang.trim() || "en",
        known_allergies: allergies.trim() || null,
      });
      pick(patient.id);
    } catch (err) {
      setAdmitError(err.message);
    }
  }

  return (
    <>
      <div className="card">
        <h2>Select a patient</h2>
        <input
          placeholder="Search by name or MRN"
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
        />
        {patients.length ? (
          patients.map((p) => (
            <div className="list-item" key={p.id}>
              <strong>{p.name}</strong>{" "}
              <span className="muted">
                Room {p.room || "-"} · MRN {p.mrn || "-"}
              </span>
              <button style={{ float: "right" }} onClick={() => pick(p.id)}>
                Select
              </button>
            </div>
          ))
        ) : (
          <p className="muted">No admitted patients match.</p>
        )}
      </div>

      <div className="card">
        <h3>Admit a new patient</h3>
        <div className="row">
          <div>
            <label>Name</label>
            <input placeholder="Full name" value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div>
            <label>MRN</label>
            <input
              placeholder="Medical record number"
              value={mrn}
              onChange={(e) => setMrn(e.target.value)}
            />
          </div>
        </div>
        <div className="row">
          <div>
            <label>Room</label>
            <input placeholder="e.g. 204A" value={room} onChange={(e) => setRoom(e.target.value)} />
          </div>
          <div>
            <label>Primary language</label>
            <input value={lang} onChange={(e) => setLang(e.target.value)} />
          </div>
        </div>
        <label>Known allergies</label>
        <input
          placeholder="e.g. penicillin"
          value={allergies}
          onChange={(e) => setAllergies(e.target.value)}
        />
        <button className="primary" onClick={admit}>
          Admit patient
        </button>
        {admitError && <div className="error">{admitError}</div>}
      </div>
    </>
  );
}
