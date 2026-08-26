import { ArrowRight, CheckCircle2, Eye, EyeOff, Headphones, LockKeyhole, Mail } from "lucide-react";
import { useState } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";

import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { ErrorNotice, PageHeader } from "../components/UI";
import { APP_NAME, PUBLIC_REGISTRATION_ENABLED } from "../config";

function homePath(user) {
  if (user?.must_change_password) return "/change-password";
  if (user?.role === "ADMIN") return "/admin/dashboard";
  if (user?.role === "IT") return "/it/dashboard";
  return "/dashboard";
}

function AuthFrame({ title, description, children, footer }) {
  return (
    <main className="auth-layout">
      <section className="auth-brand-panel">
        <div className="auth-brand">
          <span className="brand__mark brand__mark--large"><Headphones size={29} /></span>
          <span><strong>{APP_NAME}</strong><small>Teknik Destek Portalı</small></span>
        </div>
        <div className="auth-brand-panel__content">
          <p className="eyebrow eyebrow--light">Güvenli ve izlenebilir destek</p>
          <h1>Teknik destek süreciniz tek merkezde.</h1>
          <p>Talebinizi birkaç adımda iletin, gelişmeleri izleyin ve çözüm bilgisini güvenle takip edin.</p>
          <ul className="auth-benefits">
            <li><CheckCircle2 size={18} /> Kolay talep oluşturma</li>
            <li><CheckCircle2 size={18} /> Güvenli dosya paylaşımı</li>
            <li><CheckCircle2 size={18} /> Anlık durum ve çözüm takibi</li>
          </ul>
        </div>
        <p className="auth-brand-panel__foot">Ekiplerin destek süreçleri için hazırlanmıştır.</p>
      </section>
      <section className="auth-form-panel">
        <div className="auth-card">
          <div className="auth-card__heading">
            <p className="eyebrow">Teknik Destek Portalı</p>
            <h2>{title}</h2>
            <p>{description}</p>
          </div>
          {children}
          <div className="auth-card__footer">{footer}</div>
        </div>
      </section>
    </main>
  );
}

function PasswordField({ value, onChange, autoComplete = "current-password", label = "Şifre" }) {
  const [visible, setVisible] = useState(false);
  return (
    <label className="field">
      <span>{label}</span>
      <span className="input-shell">
        <LockKeyhole size={18} />
        <input
          type={visible ? "text" : "password"}
          value={value}
          onChange={onChange}
          autoComplete={autoComplete}
          required
          minLength={autoComplete === "new-password" ? 12 : 1}
          placeholder="••••••••••••"
        />
        <button type="button" className="input-shell__action" onClick={() => setVisible((shown) => !shown)} aria-label={visible ? "Şifreyi gizle" : "Şifreyi göster"}>
          {visible ? <EyeOff size={18} /> : <Eye size={18} />}
        </button>
      </span>
    </label>
  );
}

export function LoginPage() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [form, setForm] = useState({ email: "", password: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to={homePath(user)} replace />;

  async function handleSubmit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const currentUser = await login(form);
      const requestedPath = location.state?.from?.pathname;
      navigate(currentUser.must_change_password ? "/change-password" : requestedPath || homePath(currentUser), { replace: true });
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthFrame
      title="Giriş Yap"
      description="E-posta adresiniz ve şifrenizle oturum açın."
      footer={PUBLIC_REGISTRATION_ENABLED
        ? <p>Hesabınız yok mu? <Link to="/register">Yeni hesap oluşturun</Link></p>
        : <p>Bu ortamda yeni hesap kaydı yönetici tarafından yapılır.</p>}
    >
      <ErrorNotice message={error} onDismiss={() => setError("")} />
      <form className="form-stack" onSubmit={handleSubmit}>
        <label className="field">
          <span>E-posta</span>
          <span className="input-shell">
            <Mail size={18} />
            <input type="email" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} autoComplete="email" required placeholder="ad.soyad@example.com" />
          </span>
        </label>
        <PasswordField value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} />
        <button className="button button--primary button--wide" type="submit" disabled={busy}>
          {busy ? "Giriş yapılıyor…" : "Giriş yap"}
          {!busy && <ArrowRight size={18} />}
        </button>
      </form>
    </AuthFrame>
  );
}

export function RegisterPage() {
  const { user, register } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: "", password: "", first_name: "", last_name: "", phone: "", department: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to={homePath(user)} replace />;
  function update(name, value) { setForm((current) => ({ ...current, [name]: value })); }

  async function handleSubmit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await register({ ...form, phone: form.phone.trim() || null });
      navigate("/dashboard", { replace: true });
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthFrame
      title="Çalışan hesabı oluşturun"
      description="Profil bilgileriniz taleplerinizde otomatik olarak kullanılacaktır."
      footer={<p>Zaten hesabınız var mı? <Link to="/login">Giriş yapın</Link></p>}
    >
      <ErrorNotice message={error} onDismiss={() => setError("")} />
      <form className="form-stack" onSubmit={handleSubmit}>
        <div className="form-grid form-grid--two">
          <label className="field"><span>Ad</span><input value={form.first_name} onChange={(event) => update("first_name", event.target.value)} required maxLength={100} /></label>
          <label className="field"><span>Soyad</span><input value={form.last_name} onChange={(event) => update("last_name", event.target.value)} required maxLength={100} /></label>
        </div>
        <label className="field"><span>E-posta</span><input type="email" value={form.email} onChange={(event) => update("email", event.target.value)} autoComplete="email" required placeholder="ad.soyad@example.com" /></label>
        <PasswordField value={form.password} onChange={(event) => update("password", event.target.value)} autoComplete="new-password" />
        <p className="field-hint">En az 12 karakter, bir harf ve bir rakam kullanın.</p>
        <div className="form-grid form-grid--two">
          <label className="field"><span>Departman</span><input value={form.department} onChange={(event) => update("department", event.target.value)} required maxLength={150} /></label>
          <label className="field"><span>Telefon <small>(isteğe bağlı)</small></span><input type="tel" value={form.phone} onChange={(event) => update("phone", event.target.value)} maxLength={30} /></label>
        </div>
        <button className="button button--primary button--wide" type="submit" disabled={busy}>{busy ? "Hesap oluşturuluyor…" : "Hesap oluştur"}<ArrowRight size={18} /></button>
      </form>
    </AuthFrame>
  );
}

export function ChangePasswordPage() {
  const { user, setUser } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ current_password: "", new_password: "", confirmation: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event) {
    event.preventDefault();
    if (form.new_password !== form.confirmation) {
      setError("Yeni şifre ile tekrar alanı eşleşmiyor.");
      return;
    }
    setBusy(true); setError("");
    try {
      const updated = await api.changePassword({ current_password: form.current_password, new_password: form.new_password });
      setUser(updated);
      navigate(homePath(updated), { replace: true });
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page page--narrow">
      <PageHeader eyebrow="Hesap güvenliği" title={user.must_change_password ? "Geçici şifrenizi değiştirin" : "Şifrenizi değiştirin"} description={user.must_change_password ? "Yönetici tarafından verilen geçici şifreyle devam edemezsiniz. Kendinize ait güçlü bir şifre belirleyin." : "Hesabınız için yeni ve güçlü bir şifre belirleyin."} />
      <ErrorNotice message={error} onDismiss={() => setError("")} />
      <form className="card form-stack" onSubmit={submit}>
        <PasswordField label="Mevcut şifre" value={form.current_password} onChange={(event) => setForm({ ...form, current_password: event.target.value })} />
        <PasswordField label="Yeni şifre" value={form.new_password} onChange={(event) => setForm({ ...form, new_password: event.target.value })} autoComplete="new-password" />
        <PasswordField label="Yeni şifreyi tekrar girin" value={form.confirmation} onChange={(event) => setForm({ ...form, confirmation: event.target.value })} autoComplete="new-password" />
        <p className="field-hint">En az 12 karakter, bir harf ve bir rakam kullanın.</p>
        <div className="form-actions"><button className="button button--primary" type="submit" disabled={busy}>{busy ? "Şifre değiştiriliyor…" : "Şifreyi değiştir"}<ArrowRight size={18} /></button></div>
      </form>
    </div>
  );
}
