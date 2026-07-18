import { Navigate, Outlet } from "react-router-dom";
import { useApp } from "../context/AppContext";

export default function RequireStaff() {
  const { staff } = useApp();
  if (!staff) return <Navigate to="/login" replace />;
  return <Outlet />;
}
