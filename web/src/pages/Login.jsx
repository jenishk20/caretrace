import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { useApp } from "../context/AppContext";

export default function Login() {
  const { login } = useApp();
  const navigate = useNavigate();

  const [staffList, setStaffList] = useState([]);
  const [selectedId, setSelectedId] = useState("");
  const [pin, setPin] = useState("");
  const [loginError, setLoginError] = useState("");

  const [newName, setNewName] = useState("");
  const [newPin, setNewPin] = useState("");
  const [registerError, setRegisterError] = useState("");

  async function loadStaff() {
    const staff = await api.listStaff();
    setStaffList(staff);
    if (staff.length && !selectedId) setSelectedId(String(staff[0].id));
  }

  useEffect(() => {
    loadStaff();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleLogin() {
    setLoginError("");
    if (!selectedId) {
      setLoginError("Register a staff member first.");
      return;
    }
    try {
      const result = await api.login(Number(selectedId), pin);
      login(result);
      navigate("/patients");
    } catch (err) {
      setLoginError(err.message);
    }
  }

  async function handleRegister() {
    setRegisterError("");
    const name = newName.trim();
    const pinVal = newPin.trim();
    if (!name || !pinVal) {
      setRegisterError("Name and PIN are required.");
      return;
    }
    try {
      await api.createStaff(name, pinVal);
      setNewName("");
      setNewPin("");
      await loadStaff();
    } catch (err) {
      setRegisterError(err.message);
    }
  }

  return (
    <>
      <div className="card">
        <h2>Sign in</h2>
        <p className="muted">
          {staffList.length ? `${staffList.length} staff member(s) registered.` : "No staff registered yet — add one below."}
        </p>
        <div className="row" style={{ marginTop: 12 }}>
          <div>
            <label>Staff</label>
            <select value={selectedId} onChange={(e) => setSelectedId(e.target.value)}>
              {staffList.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label>PIN</label>
            <input
              type="password"
              inputMode="numeric"
              placeholder="PIN"
              value={pin}
              onChange={(e) => setPin(e.target.value)}
            />
          </div>
        </div>
        <button className="primary" onClick={handleLogin}>
          Log in
        </button>
        {loginError && <div className="error">{loginError}</div>}
      </div>

      <div className="card">
        <h3>New staff member</h3>
        <div className="row">
          <div>
            <label>Name</label>
            <input
              placeholder="e.g. Dr. Alex Rivera"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
            />
          </div>
          <div>
            <label>Choose a PIN</label>
            <input
              type="password"
              inputMode="numeric"
              placeholder="PIN"
              value={newPin}
              onChange={(e) => setNewPin(e.target.value)}
            />
          </div>
        </div>
        <button onClick={handleRegister}>Register</button>
        {registerError && <div className="error">{registerError}</div>}
      </div>
    </>
  );
}
