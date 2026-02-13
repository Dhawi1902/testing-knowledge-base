import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { adminGetUsers, adminGetStats, adminLogout } from '../services/api';

export default function AdminDashboardPage() {
  const navigate = useNavigate();
  const [users, setUsers] = useState<any[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  const adminUser = JSON.parse(localStorage.getItem('adminUser') || '{}');

  useEffect(() => {
    // Parallel AJAX calls with cookie-based session
    Promise.all([adminGetUsers(), adminGetStats()])
      .then(([userData, statsData]) => {
        setUsers(userData.users);
        setStats(statsData);
      })
      .catch((err) => {
        setError((err as Error).message);
        // If session expired, redirect to admin login
        if ((err as Error).message.includes('session') || (err as Error).message.includes('401')) {
          navigate('/admin/login');
        }
      })
      .finally(() => setLoading(false));
  }, []);

  async function handleLogout() {
    try {
      await adminLogout();
    } catch { /* ignore */ }
    localStorage.removeItem('adminUser');
    navigate('/admin/login');
  }

  if (loading) {
    return (
      <div className="page-container">
        <p>Loading admin dashboard...</p>
      </div>
    );
  }

  return (
    <div className="page-container">
      <header className="navbar admin-navbar">
        <div className="navbar-inner">
          <div className="nav-brand">
            <img src="/images/logo.svg" alt="" className="nav-logo" />
            <span className="nav-title">Admin Panel</span>
          </div>
          <div className="nav-user">
            <span className="user-info">{adminUser.displayName || 'Admin'}</span>
            <button onClick={handleLogout} className="btn-secondary" data-testid="admin-logout">
              Logout
            </button>
          </div>
        </div>
      </header>

      {error && <div className="error-message">{error}</div>}

      {/* System Stats */}
      {stats && (
        <section>
          <h2 style={{ marginBottom: '1rem' }}>System Overview</h2>
          <div className="stats-grid">
            <div className="stat-card">
              <h3>Users</h3>
              <span className="stat-number">{stats.users}</span>
            </div>
            <div className="stat-card">
              <h3>Tasks</h3>
              <span className="stat-number">{stats.tasks}</span>
            </div>
            <div className="stat-card">
              <h3>Comments</h3>
              <span className="stat-number">{stats.comments}</span>
            </div>
          </div>

          <div className="admin-breakdown">
            <div className="detail-card">
              <h3>Tasks by Status</h3>
              <table className="mini-table">
                <thead><tr><th>Status</th><th>Count</th></tr></thead>
                <tbody>
                  {stats.tasksByStatus?.map((s: any) => (
                    <tr key={s.status}>
                      <td><span className={`badge badge-${s.status}`}>{s.status.replaceAll('_', ' ')}</span></td>
                      <td>{s.count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="detail-card">
              <h3>Users by Role</h3>
              <table className="mini-table">
                <thead><tr><th>Role</th><th>Count</th></tr></thead>
                <tbody>
                  {stats.usersByRole?.map((r: any) => (
                    <tr key={r.role}>
                      <td>{r.role}</td>
                      <td>{r.count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>
      )}

      {/* Users List */}
      <section style={{ marginTop: '2rem' }}>
        <h2 style={{ marginBottom: '1rem' }}>All Users ({users.length})</h2>
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Email</th>
              <th>Display Name</th>
              <th>Role</th>
              <th>Verified</th>
              <th>Created</th>
            </tr>
          </thead>
          <tbody>
            {users.map((user: any) => (
              <tr key={user.id}>
                <td>{user.id}</td>
                <td>{user.email}</td>
                <td>{user.display_name}</td>
                <td><span className={`badge badge-role-${user.role}`}>{user.role}</span></td>
                <td>{user.is_verified ? 'Yes' : 'No'}</td>
                <td>{new Date(user.created_at).toLocaleDateString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
