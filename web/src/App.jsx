import { Navigate, Route, Routes } from "react-router-dom";
import TopBar from "./components/TopBar";
import RequireStaff from "./components/RequireStaff";
import RequirePatient from "./components/RequirePatient";
import Login from "./pages/Login";
import PatientPicker from "./pages/PatientPicker";
import Dashboard from "./pages/Dashboard";
import Scribe from "./pages/Scribe";
import Translate from "./pages/Translate";
import Consent from "./pages/Consent";
import Discharge from "./pages/Discharge";
import Handoff from "./pages/Handoff";
import Orientation from "./pages/Orientation";

export default function App() {
  return (
    <>
      <TopBar />
      <main id="app">
        <Routes>
          <Route path="/login" element={<Login />} />

          <Route element={<RequireStaff />}>
            <Route path="/patients" element={<PatientPicker />} />

            <Route element={<RequirePatient />}>
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/scribe" element={<Scribe />} />
              <Route path="/translate" element={<Translate />} />
              <Route path="/consent" element={<Consent />} />
              <Route path="/discharge" element={<Discharge />} />
              <Route path="/handoff" element={<Handoff />} />
              <Route path="/orientation" element={<Orientation />} />
            </Route>
          </Route>

          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </main>
    </>
  );
}
