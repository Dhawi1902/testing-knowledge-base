import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { adminGetLoginPage, adminLogin } from '../services/api';

export default function AdminLoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [csrf, setCsrf] = useState('');
  const [formId, setFormId] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // GET /admin/login sets the SESSIONID cookie and returns CSRF tokens
    adminGetLoginPage()
      .then((data) => {
        setCsrf(data._csrf);
        setFormId(data._formId);
      })
      .catch(() => setError('Failed to load admin login page.'));
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const result = await adminLogin(email, password, csrf, formId);
      // Store admin user info (separate from regular user)
      localStorage.setItem('adminUser', JSON.stringify(result.user));
      navigate('/admin/dashboard');
    } catch (err) {
      setError((err as Error).message);
      // Refresh CSRF tokens
      try {
        const data = await adminGetLoginPage();
        setCsrf(data._csrf);
        setFormId(data._formId);
      } catch { /* ignore */ }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-container admin-login">
      <div className="login-card">
        <img src="/images/logo.svg" alt="TaskFlow" className="login-logo" />
        <h1>Admin Panel</h1>
        <p className="login-subtitle">Administrator access only</p>

        {error && <div className="error-message">{error}</div>}

        <form onSubmit={handleSubmit}>
          {/* Hidden CSRF tokens — JMeter extracts these for TC09 */}
          <input type="hidden" name="_csrf" value={csrf} />
          <input type="hidden" name="_formId" value={formId} />

          <div className="form-group">
            <label htmlFor="admin-email">Email</label>
            <input
              id="admin-email"
              type="email"
              name="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="admin@taskflow.local"
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="admin-password">Password</label>
            <input
              id="admin-password"
              type="password"
              name="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="admin123"
              required
            />
          </div>

          <button type="submit" className="btn-primary" disabled={loading || !csrf}>
            {loading ? 'Signing in...' : 'Sign In as Admin'}
          </button>
        </form>
      </div>
    </div>
  );
}
