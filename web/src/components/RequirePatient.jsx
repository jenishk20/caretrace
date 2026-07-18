import { Navigate, Outlet } from "react-router-dom";
import { useApp } from "../context/AppContext";

export default function RequirePatient() {
  const { patientId } = useApp();
  if (!patientId) return <Navigate to="/patients" replace />;
  return <Outlet />;
}
