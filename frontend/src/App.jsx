import { Navigate, Route, Routes, useLocation } from "react-router-dom";

import { useAuth } from "./auth/AuthContext";
import AppShell from "./components/AppShell";
import { LoadingScreen } from "./components/UI";
import { PUBLIC_REGISTRATION_ENABLED } from "./config";
import { ChangePasswordPage, LoginPage, RegisterPage } from "./pages/AuthPages";
import {
  AdminAuditPage,
  AdminCannedResponsesPage,
  AdminDashboardPage,
  AdminTicketDetailPage,
  AdminTicketsPage,
  AdminUsersPage,
} from "./pages/AdminPages";
import {
  ItDashboardPage,
  ItTicketDetailPage,
  ItTicketsPage,
  ReportsPage,
  SystemMonitoringPage,
} from "./pages/ItPages";
import {
  NewTicketPage,
  NotificationsPage,
  ProfilePage,
  UserDashboardPage,
  UserTicketDetailPage,
  UserTicketsPage,
} from "./pages/UserPages";

function ProtectedLayout() {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading)
    return (
      <div className="boot-screen">
        <LoadingScreen label="Oturum doğrulanıyor…" />
      </div>
    );
  if (!user) return <Navigate to="/login" state={{ from: location }} replace />;
  if (user.must_change_password && location.pathname !== "/change-password") {
    return <Navigate to="/change-password" replace />;
  }
  return <AppShell />;
}

function homePath(user) {
  if (user?.must_change_password) return "/change-password";
  if (user?.role === "ADMIN") return "/admin/dashboard";
  if (user?.role === "IT") return "/it/dashboard";
  return "/dashboard";
}

function RoleRoute({ role, roles, children }) {
  const { user } = useAuth();
  const allowedRoles = roles || [role];
  if (!allowedRoles.includes(user?.role)) {
    return <Navigate to={homePath(user)} replace />;
  }
  return children;
}

function HomeRedirect() {
  const { user, loading } = useAuth();
  if (loading)
    return (
      <div className="boot-screen">
        <LoadingScreen />
      </div>
    );
  if (!user) return <Navigate to="/login" replace />;
  return <Navigate to={homePath(user)} replace />;
}

function NotFoundPage() {
  return (
    <div className="not-found">
      <span>404</span>
      <h1>Sayfa bulunamadı</h1>
      <p>Aradığınız sayfa taşınmış veya mevcut olmayabilir.</p>
      <a className="button button--primary" href="/">
        Ana sayfaya dön
      </a>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/register"
        element={PUBLIC_REGISTRATION_ENABLED ? <RegisterPage /> : <Navigate to="/login" replace />}
      />
      <Route path="/" element={<HomeRedirect />} />
      <Route element={<ProtectedLayout />}>
        <Route path="change-password" element={<ChangePasswordPage />} />
        <Route
          path="dashboard"
          element={
            <RoleRoute role="USER">
              <UserDashboardPage />
            </RoleRoute>
          }
        />
        <Route
          path="tickets"
          element={
            <RoleRoute role="USER">
              <UserTicketsPage />
            </RoleRoute>
          }
        />
        <Route
          path="tickets/new"
          element={
            <RoleRoute role="USER">
              <NewTicketPage />
            </RoleRoute>
          }
        />
        <Route
          path="tickets/:id"
          element={
            <RoleRoute role="USER">
              <UserTicketDetailPage />
            </RoleRoute>
          }
        />
        <Route path="notifications" element={<NotificationsPage />} />
        <Route path="profile" element={<ProfilePage />} />
        <Route
          path="it/dashboard"
          element={
            <RoleRoute role="IT">
              <ItDashboardPage />
            </RoleRoute>
          }
        />
        <Route
          path="it/tickets"
          element={
            <RoleRoute role="IT">
              <ItTicketsPage />
            </RoleRoute>
          }
        />
        <Route
          path="it/my-tickets"
          element={
            <RoleRoute role="IT">
              <ItTicketsPage defaultView="mine" />
            </RoleRoute>
          }
        />
        <Route
          path="it/tickets/:id"
          element={
            <RoleRoute role="IT">
              <ItTicketDetailPage />
            </RoleRoute>
          }
        />
        <Route
          path="it/reports"
          element={
            <RoleRoute role="IT">
              <ReportsPage />
            </RoleRoute>
          }
        />
        <Route
          path="it/system"
          element={
            <RoleRoute roles={["IT", "ADMIN"]}>
              <SystemMonitoringPage />
            </RoleRoute>
          }
        />
        <Route
          path="admin/dashboard"
          element={
            <RoleRoute role="ADMIN">
              <AdminDashboardPage />
            </RoleRoute>
          }
        />
        <Route
          path="admin/users"
          element={
            <RoleRoute role="ADMIN">
              <AdminUsersPage />
            </RoleRoute>
          }
        />
        <Route
          path="admin/tickets"
          element={
            <RoleRoute role="ADMIN">
              <AdminTicketsPage />
            </RoleRoute>
          }
        />
        <Route
          path="admin/tickets/:id"
          element={
            <RoleRoute role="ADMIN">
              <AdminTicketDetailPage />
            </RoleRoute>
          }
        />
        <Route
          path="admin/canned-responses"
          element={
            <RoleRoute role="ADMIN">
              <AdminCannedResponsesPage />
            </RoleRoute>
          }
        />
        <Route
          path="admin/reports"
          element={
            <RoleRoute role="ADMIN">
              <ReportsPage />
            </RoleRoute>
          }
        />
        <Route
          path="admin/audit"
          element={
            <RoleRoute role="ADMIN">
              <AdminAuditPage />
            </RoleRoute>
          }
        />
      </Route>
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
