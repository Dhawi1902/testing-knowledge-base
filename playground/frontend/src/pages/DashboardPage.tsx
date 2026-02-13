import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import Navbar from '../components/Navbar';
import { getDashboardStats, getDashboardRecent } from '../services/api';

interface TaskStats {
  byStatus: Array<{ status: string; count: string }>;
  total: number;
}

interface RecentData {
  recentTasks: Array<{ id: number; title: string; status: string; updated_at: string; assignee_name: string }>;
  recentComments: Array<{ id: number; content: string; created_at: string; task_id: number; author_name: string; task_title: string }>;
}

export default function DashboardPage() {
  const [stats, setStats] = useState<TaskStats | null>(null);
  const [recent, setRecent] = useState<RecentData | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    // Parallel AJAX calls - TC01 tests this
    Promise.all([getDashboardStats(), getDashboardRecent()])
      .then(([statsData, recentData]) => {
        setStats(statsData as TaskStats);
        setRecent(recentData as RecentData);
      })
      .catch((err) => {
        setError((err as Error).message);
      });
  }, []);

  return (
    <>
      <Navbar />
      <main className="page-container">
        <h1>Dashboard</h1>

        {error && <div className="error-message">{error}</div>}

        {stats && (
          <section className="stats-grid">
            <div className="stat-card">
              <h3>Total Tasks</h3>
              <span className="stat-number">{stats.total}</span>
            </div>
            {stats.byStatus.map((s) => (
              <div key={s.status} className="stat-card">
                <h3>{s.status.replace('_', ' ')}</h3>
                <span className="stat-number">{s.count}</span>
              </div>
            ))}
          </section>
        )}

        {recent && (
          <section className="recent-activity">
            <h2>Recent Tasks</h2>
            <table>
              <thead>
                <tr>
                  <th>Title</th>
                  <th>Status</th>
                  <th>Assignee</th>
                  <th>Updated</th>
                </tr>
              </thead>
              <tbody>
                {recent.recentTasks.map((task) => (
                  <tr key={task.id}>
                    <td><Link to={`/tasks/${task.id}`}>{task.title}</Link></td>
                    <td><span className={`badge badge-${task.status}`}>{task.status.replaceAll('_', ' ')}</span></td>
                    <td>{task.assignee_name || '—'}</td>
                    <td>{new Date(task.updated_at).toLocaleDateString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        )}
      </main>
    </>
  );
}
