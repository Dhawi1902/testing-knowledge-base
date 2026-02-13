import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useToast } from '../components/Toast';
import Navbar from '../components/Navbar';
import { getTasks, getCsrfTokens, approveTask, rejectTask } from '../services/api';

export default function ReviewQueuePage() {
  const navigate = useNavigate();
  const { addToast } = useToast();
  const [tasks, setTasks] = useState<Array<Record<string, any>>>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [actionLoading, setActionLoading] = useState<number | null>(null);
  const [rejectModal, setRejectModal] = useState<{ taskId: number; title: string } | null>(null);
  const [remarks, setRemarks] = useState('');

  const userRole = JSON.parse(localStorage.getItem('user') || '{}').role;

  useEffect(() => {
    if (userRole !== 'manager' && userRole !== 'admin') {
      navigate('/dashboard');
      return;
    }
    loadTasks();
  }, []);

  async function loadTasks() {
    try {
      setLoading(true);
      const data = await getTasks({ status: 'pending_review', limit: '100' });
      setTasks(data.tasks);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleApprove(taskId: number) {
    try {
      setActionLoading(taskId);
      const csrf = await getCsrfTokens();
      await approveTask(taskId, csrf._csrf, csrf._formId);
      setTasks(tasks.filter(t => t.id !== taskId));
      addToast('Task approved');
    } catch (err: any) {
      addToast(err.message, 'error');
    } finally {
      setActionLoading(null);
    }
  }

  async function handleReject() {
    if (!rejectModal || !remarks.trim()) return;
    try {
      setActionLoading(rejectModal.taskId);
      const csrf = await getCsrfTokens();
      await rejectTask(rejectModal.taskId, remarks, csrf._csrf, csrf._formId);
      setTasks(tasks.filter(t => t.id !== rejectModal.taskId));
      setRejectModal(null);
      setRemarks('');
      addToast('Task rejected');
    } catch (err: any) {
      addToast(err.message, 'error');
    } finally {
      setActionLoading(null);
    }
  }

  if (loading) {
    return (
      <><Navbar /><main className="page-container"><p>Loading review queue...</p></main></>
    );
  }

  return (
    <>
      <Navbar />
      <main className="page-container">
        <h1>Review Queue</h1>

        {error && <div className="error-message">{error}</div>}

        {tasks.length === 0 ? (
          <p>No tasks pending review.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Title</th>
                <th>Priority</th>
                <th>Creator</th>
                <th>Assignee</th>
                <th>Created</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {tasks.map((task: any) => (
                <tr key={task.id}>
                  <td>{task.id}</td>
                  <td>{task.title}</td>
                  <td>{task.priority}</td>
                  <td>{task.creator_name}</td>
                  <td>{task.assignee_name || '—'}</td>
                  <td>{new Date(task.created_at).toLocaleDateString()}</td>
                  <td className="action-cell">
                    <button
                      onClick={() => handleApprove(task.id)}
                      disabled={actionLoading === task.id}
                      className="btn-approve"
                      data-testid={`approve-${task.id}`}
                    >
                      {actionLoading === task.id ? '...' : 'Approve'}
                    </button>
                    <button
                      onClick={() => setRejectModal({ taskId: task.id, title: task.title })}
                      disabled={actionLoading === task.id}
                      className="btn-reject"
                      data-testid={`reject-${task.id}`}
                    >
                      Reject
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {rejectModal && (
          <div className="modal-overlay" data-testid="reject-modal">
            <div className="modal">
              <h3>Reject: {rejectModal.title}</h3>
              <textarea
                value={remarks}
                onChange={e => setRemarks(e.target.value)}
                placeholder="Enter rejection remarks (required)"
                rows={4}
                style={{ width: '100%', marginBottom: '1rem' }}
                data-testid="reject-remarks"
              />
              <div className="modal-actions">
                <button onClick={() => { setRejectModal(null); setRemarks(''); }} className="btn-secondary">Cancel</button>
                <button onClick={handleReject} disabled={!remarks.trim()} className="btn-danger">Reject Task</button>
              </div>
            </div>
          </div>
        )}
      </main>
    </>
  );
}
