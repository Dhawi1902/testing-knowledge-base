import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { getCsrfTokens, login } from '../services/api';

export default function LoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [csrf, setCsrf] = useState('');
  const [formId, setFormId] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  // Fetch CSRF tokens on page load
  useEffect(() => {
    getCsrfTokens()
      .then((tokens) => {
        setCsrf(tokens._csrf);
        setFormId(tokens._formId);
      })
      .catch((err) => {
        console.error('Failed to fetch CSRF tokens:', err);
        setError('Failed to load form. Please refresh.');
      });
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const result = await login(email, password, csrf, formId);
      localStorage.setItem('accessToken', result.accessToken);
      localStorage.setItem('refreshToken', result.refreshToken);
      localStorage.setItem('user', JSON.stringify(result.user));
      navigate('/dashboard');
    } catch (err) {
      setError((err as Error).message);
      // Refresh CSRF tokens after failed attempt
      try {
        const tokens = await getCsrfTokens();
        setCsrf(tokens._csrf);
        setFormId(tokens._formId);
      } catch {
        // Ignore refresh failure
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-container">
      <div className="login-card">
        <img src="/images/logo.svg" alt="TaskFlow" className="login-logo" />
        <h1>TaskFlow</h1>
        <p className="login-subtitle">Sign in to your account</p>

        {error && <div className="error-message">{error}</div>}

        <form onSubmit={handleSubmit}>
          {/* Hidden CSRF tokens - JMeter extracts these */}
          <input type="hidden" name="_csrf" value={csrf} />
          <input type="hidden" name="_formId" value={formId} />

          <div className="form-group">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              name="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="user01@taskflow.local"
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              name="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="password01"
              required
            />
          </div>

          <button type="submit" className="btn-primary" disabled={loading || !csrf}>
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>

        <p style={{ marginTop: '1rem', fontSize: '0.875rem' }}>
          Don't have an account? <Link to="/register">Register</Link>
        </p>
      </div>
    </div>
  );
}
