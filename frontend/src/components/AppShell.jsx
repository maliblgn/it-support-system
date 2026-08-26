import {
  Activity,
  BarChart3,
  Bell,
  ClipboardList,
  Headphones,
  House,
  LogOut,
  Menu,
  PlusSquare,
  ListChecks,
  MessageSquareText,
  Search,
  Settings,
  ShieldCheck,
  Trash2,
  UserRound,
  Users,
  X,
} from "lucide-react";
import { useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { APP_NAME } from "../config";
import { initials } from "../utils/format";

const USER_NAV = [
  { to: "/dashboard", label: "Ana Sayfa", icon: House },
  { to: "/tickets/new", label: "Yeni Talep", icon: PlusSquare },
  { to: "/tickets", label: "Taleplerim", icon: ClipboardList },
  { to: "/notifications", label: "Bildirimler", icon: Bell },
];

const IT_NAV = [
  { to: "/it/dashboard", label: "IT Özeti", icon: House },
  { to: "/it/tickets", label: "Talep Havuzu", icon: ClipboardList },
  { to: "/it/my-tickets", label: "Benim Ticketlarım", icon: ListChecks },
  { to: "/it/reports", label: "Raporlar", icon: BarChart3 },
  { to: "/it/system", label: "Sistem İzleme", icon: Activity },
  { to: "/notifications", label: "Bildirimler", icon: Bell },
];

const ADMIN_NAV = [
  { to: "/admin/dashboard", label: "Yönetim Özeti", icon: House },
  { to: "/admin/users", label: "Kullanıcılar", icon: Users },
  { to: "/admin/tickets", label: "Talep Yönetimi", icon: Trash2 },
  {
    to: "/admin/canned-responses",
    label: "Hazır Yanıtlar",
    icon: MessageSquareText,
  },
  { to: "/admin/reports", label: "Raporlar", icon: BarChart3 },
  { to: "/admin/audit", label: "Denetim Kayıtları", icon: ShieldCheck },
  { to: "/it/system", label: "Sistem İzleme", icon: Activity },
  { to: "/notifications", label: "Bildirimler", icon: Bell },
];

function getPageLabel(pathname, role) {
  if (pathname.includes("/tickets/new")) return "Yeni Talep Oluştur";
  if (/\/tickets\/\d+/.test(pathname)) return "Talep Detayı";
  if (pathname === "/tickets") return "Taleplerim";
  if (pathname === "/it/tickets") return "Bilgi İşlem Talep Havuzu";
  if (pathname === "/it/my-tickets") return "Benim Ticketlarım";
  if (pathname === "/it/reports") return "Raporlar";
  if (pathname === "/it/system") return "Sistem İzleme";
  if (pathname === "/admin/users") return "Kullanıcı Yönetimi";
  if (pathname === "/admin/tickets") return "Talep ve Geri Dönüşüm Yönetimi";
  if (pathname === "/admin/canned-responses") return "Hazır Yanıtlar";
  if (pathname === "/admin/reports") return "Raporlar";
  if (pathname === "/admin/audit") return "Denetim Kayıtları";
  if (pathname === "/change-password") return "Şifre Değişikliği";
  if (pathname === "/notifications") return "Bildirimler";
  if (pathname === "/profile") return "Profilim";
  if (role === "ADMIN") return "Yönetim Portalı";
  return role === "IT" ? "IT Destek Portalı" : "Çalışan Destek Portalı";
}

export default function AppShell() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [globalSearch, setGlobalSearch] = useState("");
  const navigation =
    user.role === "ADMIN" ? ADMIN_NAV : user.role === "IT" ? IT_NAV : USER_NAV;

  function isNavigationActive(to) {
    const { pathname } = location;
    if (to === "/tickets/new") return pathname === to;
    if (to === "/tickets")
      return pathname === to || /^\/tickets\/\d+/.test(pathname);
    if (to === "/it/tickets")
      return pathname === to || pathname.startsWith(`${to}/`);
    if (to === "/it/my-tickets") return pathname === to;
    if (to === "/admin/tickets")
      return pathname === to || pathname.startsWith(`${to}/`);
    return pathname === to;
  }

  async function handleLogout() {
    await logout();
    navigate("/login", { replace: true });
  }

  function submitGlobalSearch(event) {
    event.preventDefault();
    const value = globalSearch.trim();
    if (!value || !["IT", "ADMIN"].includes(user.role)) return;
    navigate(
      user.role === "ADMIN"
        ? `/admin/tickets?search=${encodeURIComponent(value)}`
        : `/it/tickets?view=all&search=${encodeURIComponent(value)}`,
    );
  }

  return (
    <div className="app-shell">
      {mobileOpen && (
        <button
          className="sidebar-scrim"
          aria-label="Menüyü kapat"
          onClick={() => setMobileOpen(false)}
        />
      )}
      <aside className={`sidebar ${mobileOpen ? "sidebar--open" : ""}`}>
        <div className="brand">
          <span className="brand__mark">
            <Headphones size={22} />
          </span>
          <span>
            <strong>{APP_NAME}</strong>
            <small>Teknik Destek Portalı</small>
          </span>
        </div>
        <button
          className="sidebar__mobile-close"
          type="button"
          onClick={() => setMobileOpen(false)}
          aria-label="Menüyü kapat"
        >
          <X size={20} />
        </button>
        <div className="sidebar__context">
          <span>
            {user.role === "ADMIN"
              ? "Yönetim Alanı"
              : user.role === "IT"
                ? "Bilgi İşlem Alanı"
                : "Çalışan Alanı"}
          </span>
          <strong>{user.department}</strong>
        </div>
        <nav className="sidebar__nav" aria-label="Ana menü">
          {navigation.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              onClick={() => setMobileOpen(false)}
              className={`nav-item ${isNavigationActive(to) ? "nav-item--active" : ""}`}
            >
              <Icon size={19} />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="sidebar__footer">
          <NavLink
            to="/profile"
            onClick={() => setMobileOpen(false)}
            className={({ isActive }) =>
              `nav-item ${isActive ? "nav-item--active" : ""}`
            }
          >
            <UserRound size={19} />
            <span>Profilim</span>
          </NavLink>
          <button
            className="nav-item nav-item--button nav-item--danger"
            type="button"
            onClick={handleLogout}
          >
            <LogOut size={19} />
            <span>Çıkış Yap</span>
          </button>
        </div>
      </aside>

      <div className="workspace">
        <header className="topbar">
          <div className="topbar__title-group">
            <button
              className="mobile-menu-button"
              type="button"
              onClick={() => setMobileOpen(true)}
              aria-label="Menüyü aç"
            >
              <Menu size={21} />
            </button>
            <strong>{getPageLabel(location.pathname, user.role)}</strong>
          </div>
          <div className="topbar__actions">
            {["IT", "ADMIN"].includes(user.role) && (
              <form
                className="global-search"
                onSubmit={submitGlobalSearch}
                role="search"
              >
                <Search size={17} aria-hidden="true" />
                <input
                  value={globalSearch}
                  onChange={(event) => setGlobalSearch(event.target.value)}
                  placeholder="Talep no, kullanıcı veya konu ara…"
                  aria-label="Taleplerde ara"
                />
              </form>
            )}
            <button
              className="topbar-icon"
              type="button"
              onClick={() => navigate("/notifications")}
              aria-label="Bildirimleri aç"
            >
              <Bell size={20} />
            </button>
            <button
              className="topbar-icon"
              type="button"
              onClick={() => navigate("/profile")}
              aria-label="Profil ayarlarını aç"
            >
              <Settings size={20} />
            </button>
            <button
              className="topbar-avatar"
              type="button"
              onClick={() => navigate("/profile")}
              aria-label={`${user.first_name} ${user.last_name} profilini aç`}
            >
              {initials(user)}
            </button>
          </div>
        </header>
        <main className="app-main">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
