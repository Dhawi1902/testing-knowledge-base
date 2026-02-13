import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useToast } from '../components/Toast';
import Navbar from '../components/Navbar';
import { getBatchEditData, submitBatchUpdate, getUsers } from '../services/api';

interface TaskRow {
  id: number;
  title: string;
  status: string;
  priority: string;
  assignee_id: number | null;
  assignee_name: string | null;
  // Edited values (undefined = unchanged)
  editStatus?: string;
  editPriority?: string;
  editAssignee?: string;
  changed?: boolean;
}

const STATUSES = ['open', 'in_progress', 'completed', 'pending_review', 'approved', 'rejected'];
const PRIORITIES = ['low', 'medium', 'high', 'urgent'];

export default function BatchEditPage() {
  const navigate = useNavigate();
  const { addToast } = useToast();

  const [tasks, setTasks] = useState<TaskRow[]>([]);
  const [users, setUsers] = useState<any[]>([]);
  const [csrf, setCsrf] = useState('');
  const [formId, setFormId] = useState('');
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<any>(null);

  useEffect(() => {
    Promise.all([getBatchEditData(), getUsers()])
      .then(([batchData, userData]) => {
        setTasks(batchData.tasks.map((t: any) => ({
          ...t,
          editStatus: t.status,
          editPriority: t.priority,
          editAssignee: t.assignee_id ? String(t.assignee_id) : '',
          changed: false,
        })));
        setCsrf(batchData._csrf);
        setFormId(batchData._formId);
        setUsers(userData.users);
      })
      .catch((err) => setError((err as Error).message))
      .finally(() => setLoading(false));
  }, []);

  function handleFieldChange(taskId: number, field: 'editStatus' | 'editPriority' | 'editAssignee', value: string) {
    setTasks(prev =>
      prev.map(t => {
        if (t.id !== taskId) return t;
        const updated = { ...t, [field]: value };
        // Mark as changed if any field differs from original
        updated.changed =
          updated.editStatus !== t.status ||
          updated.editPriority !== t.priority ||
          updated.editAssignee !== (t.assignee_id ? String(t.assignee_id) : '');
        return updated;
      })
    );
  }

  async function handleSubmit() {
    const changedTasks = tasks.filter(t => t.changed);
    if (changedTasks.length === 0) {
      addToast('No changes to submit', 'info');
      return;
    }

    setSubmitting(true);
    setResult(null);

    // Build changesList JSON — this is what the JS engine builds in the browser
    // JMeter needs Groovy to replicate this: {"1":{"ID":"42","STS":"in_progress","PRI":"high","ASG":"3"}, ...}
    const changesList: Record<string, { ID: string; STS: string; PRI: string; ASG: string }> = {};
    changedTasks.forEach((t, index) => {
      changesList[String(index + 1)] = {
        ID: String(t.id),
        STS: t.editStatus || t.status,
        PRI: t.editPriority || t.priority,
        ASG: t.editAssignee || '',
      };
    });

    // Submit as URL-encoded JSON string
    const changesListJson = JSON.stringify(changesList);

    try {
      const res = await submitBatchUpdate(changesListJson, csrf, formId);
      setResult(res);
      addToast(res.message);
    } catch (err) {
      addToast((err as Error).message, 'error');
    } finally {
      setSubmitting(false);
    }
  }

  const changedCount = tasks.filter(t => t.changed).length;

  if (loading) {
    return (
      <><Navbar /><main className="page-container"><p>Loading batch edit...</p></main></>
    );
  }

  return (
    <>
      <Navbar />
      <main className="page-container">
        <div className="detail-header">
          <h1>Batch Edit Tasks</h1>
          <div className="detail-actions">
            <span style={{ fontSize: '0.875rem', color: '#666' }}>
              {changedCount} task{changedCount !== 1 ? 's' : ''} modified
            </span>
            <button
              onClick={() => navigate('/tasks')}
              className="btn-secondary"
            >
              Cancel
            </button>
            <button
              onClick={handleSubmit}
              disabled={submitting || changedCount === 0}
              className="btn-primary"
              style={{ width: 'auto' }}
              data-testid="batch-submit"
            >
              {submitting ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </div>

        {error && <div className="error-message">{error}</div>}

        {result && (
          <div className="success-message" data-testid="batch-result">
            {result.message}
            {result.errors?.length > 0 && (
              <ul>
                {result.errors.map((e: any, i: number) => (
                  <li key={i}>Task {e.taskId}: {e.error}</li>
                ))}
              </ul>
            )}
          </div>
        )}

        {/* Hidden CSRF tokens for JMeter extraction */}
        <input type="hidden" name="_csrf" value={csrf} />
        <input type="hidden" name="_formId" value={formId} />

        <table data-testid="batch-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Title</th>
              <th>Status</th>
              <th>Priority</th>
              <th>Assignee</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {tasks.map((task) => (
              <tr key={task.id} className={task.changed ? 'row-changed' : ''}>
                <td>{task.id}</td>
                <td>{task.title}</td>
                <td>
                  <select
                    value={task.editStatus}
                    onChange={(e) => handleFieldChange(task.id, 'editStatus', e.target.value)}
                    data-testid={`status-${task.id}`}
                  >
                    {STATUSES.map(s => <option key={s} value={s}>{s.replaceAll('_', ' ')}</option>)}
                  </select>
                </td>
                <td>
                  <select
                    value={task.editPriority}
                    onChange={(e) => handleFieldChange(task.id, 'editPriority', e.target.value)}
                    data-testid={`priority-${task.id}`}
                  >
                    {PRIORITIES.map(p => <option key={p} value={p}>{p}</option>)}
                  </select>
                </td>
                <td>
                  <select
                    value={task.editAssignee}
                    onChange={(e) => handleFieldChange(task.id, 'editAssignee', e.target.value)}
                    data-testid={`assignee-${task.id}`}
                  >
                    <option value="">Unassigned</option>
                    {users.map(u => <option key={u.id} value={u.id}>{u.display_name}</option>)}
                  </select>
                </td>
                <td>
                  {task.changed && <span className="badge badge-in_progress">modified</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </main>
    </>
  );
}
