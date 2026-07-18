import { Navigate, Route, Routes } from "react-router-dom";
import Landing from "./pages/Landing.jsx";
import DoctorLogin from "./pages/DoctorLogin.jsx";
import Roster from "./pages/Roster.jsx";
import Workspace from "./pages/Workspace.jsx";
import PatientLogin from "./pages/PatientLogin.jsx";
import PatientHome from "./pages/PatientHome.jsx";
import { session } from "./lib/session.js";

function RequireStaff({ children }) {
  return session.staff() ? children : <Navigate to="/doctor/login" replace />;
}
function RequirePatient({ children }) {
  return session.patient() ? children : <Navigate to="/patient/login" replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/doctor/login" element={<DoctorLogin />} />
      <Route path="/doctor" element={<RequireStaff><Roster /></RequireStaff>} />
      <Route path="/doctor/patient/:id/*" element={<RequireStaff><Workspace /></RequireStaff>} />
      <Route path="/patient/login" element={<PatientLogin />} />
      <Route path="/patient" element={<RequirePatient><PatientHome /></RequirePatient>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
