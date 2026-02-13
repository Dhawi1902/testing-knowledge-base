import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { getCsrfTokens, register } from '../services/api';

export default function RegisterPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [csrf, setCsrf] = useState('');
  const [formId, setFormId] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    getCsrfTokens()
      .then((tokens) => {
        setCsrf(tokens._csrf);
        setFormId(tokens._formId);
      })
      .catch(() => setError('Failed to load form. Please refresh.'));
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setSuccess('');
    setLoading(true);

    try {
      const result = await register(email, password, displayName, csrf, formId);
      setSuccess(`Registration successful! Verification URL: ${result.verificationUrl}`);
    } catch (err) {
      setError((err as Error).message);
      try {
        const tokens = await getCsrfTokens();
        setCsrf(tokens._csrf);
        setFormId(tokens._formId);
      } catch { /* ignore */ }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-container">
      <div className="login-card">
        <img src="/images/logo.svg" alt="TaskFlow" className="login-logo" />
        <h1>TaskFlow</h1>
        <p className="login-subtitle">Create your account</p>

        {error && <div className="error-message">{error}</div>}
        {success && (
          <div className="success-message" data-testid="register-success">
            {success}
            <br />
            <Link to="/login" style={{ marginTop: '0.5rem', display: 'inline-block' }}>
              Go to Login
            </Link>
          </div>
        )}

        {!success && (
          <form onSubmit={handleSubmit}>
            <input type="hidden" name="_csrf" value={csrf} />
            <input type="hidden" name="_formId" value={formId} />

            <div className="form-group">
              <label htmlFor="displayName">Display Name</label>
              <input
                id="displayName"
                type="text"
                name="displayName"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                placeholder="John Doe"
                required
              />
            </div>

            <div className="form-group">
              <label htmlFor="email">Email</label>
              <input
                id="email"
                type="email"
                name="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
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
                required
              />
            </div>

            <button type="submit" className="btn-primary" disabled={loading || !csrf}>
              {loading ? 'Registering...' : 'Register'}
            </button>
          </form>
        )}

        <p style={{ marginTop: '1rem', fontSize: '0.875rem' }}>
          Already have an account? <Link to="/login">Sign in</Link>
        </p>
      </div>
    </div>
  );
}
