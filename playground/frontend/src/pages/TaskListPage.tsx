import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import Navbar from '../components/Navbar';
import { getTasks } from '../services/api';

interface Task {
  id: number;
  title: string;
  status: string;
  priority: string;
  project_code: string;
  assignee_name: string;
  creator_name: string;
  created_at: string;
}

interface Pagination {
  page: number;
  limit: number;
  total: number;
  totalPages: number;
}

export default function TaskListPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [pagination, setPagination] = useState<Pagination | null>(null);
  const [statusFilter, setStatusFilter] = useState('');
  const [page, setPage] = useState(1);
  const [error, setError] = useState('');

  useEffect(() => {
    const params: Record<string, string> = { page: String(page) };
    if (statusFilter) params.status = statusFilter;

    getTasks(params)
      .then((data) => {
        setTasks(data.tasks as unknown as Task[]);
        setPagination(data.pagination);
      })
      .catch((err) => setError((err as Error).message));
  }, [page, statusFilter]);

  return (
    <>
      <Navbar />
      <main className="page-container">
        <div className="detail-header">
          <h1>Tasks</h1>
          <div className="detail-actions">
            <Link to="/tasks/new" className="btn-primary" style={{ textDecoration: 'none', width: 'auto', padding: '0.5rem 1rem', marginTop: 0 }}>
              New Task
            </Link>
            <Link to="/tasks/batch-edit" className="btn-secondary" style={{ textDecoration: 'none', padding: '0.5rem 1rem' }}>
              Batch Edit
            </Link>
          </div>
        </div>

        {error && <div className="error-message">{error}</div>}

        <div className="filters">
          <label>
            Status:
            <select value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}>
              <option value="">All</option>
              <option value="open">Open</option>
              <option value="in_progress">In Progress</option>
              <option value="completed">Completed</option>
              <option value="pending_review">Pending Review</option>
              <option value="approved">Approved</option>
              <option value="rejected">Rejected</option>
            </select>
          </label>
        </div>

        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Title</th>
              <th>Status</th>
              <th>Priority</th>
              <th>Project</th>
              <th>Assignee</th>
              <th>Created</th>
            </tr>
          </thead>
          <tbody>
            {tasks.map((task) => (
              <tr key={task.id} className="clickable-row">
                <td>{task.id}</td>
                <td><Link to={`/tasks/${task.id}`}>{task.title}</Link></td>
                <td><span className={`badge badge-${task.status}`}>{task.status.replaceAll('_', ' ')}</span></td>
                <td>{task.priority}</td>
                <td>{task.project_code || '—'}</td>
                <td>{task.assignee_name || '—'}</td>
                <td>{new Date(task.created_at).toLocaleDateString()}</td>
              </tr>
            ))}
          </tbody>
        </table>

        {pagination && pagination.totalPages > 1 && (
          <div className="pagination">
            <button onClick={() => setPage(page - 1)} disabled={page <= 1}>Previous</button>
            <span>Page {pagination.page} of {pagination.totalPages}</span>
            <button onClick={() => setPage(page + 1)} disabled={page >= pagination.totalPages}>Next</button>
          </div>
        )}
      </main>
    </>
  );
}
