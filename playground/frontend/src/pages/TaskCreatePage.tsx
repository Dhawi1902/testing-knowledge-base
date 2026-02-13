import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useToast } from '../components/Toast';
import Navbar from '../components/Navbar';
import { getCsrfTokens, createTask, getUsers } from '../services/api';

interface User {
  id: number;
  email: string;
  display_name: string;
  role: string;
}

export default function TaskCreatePage() {
  const navigate = useNavigate();
  const { addToast } = useToast();
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [priority, setPriority] = useState('medium');
  const [assigneeId, setAssigneeId] = useState('');
  const [projectCode, setProjectCode] = useState('');
  const [csrf, setCsrf] = useState('');
  const [formId, setFormId] = useState('');
  const [users, setUsers] = useState<User[]>([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // Fetch CSRF tokens and user list in parallel
    Promise.all([getCsrfTokens(), getUsers()])
      .then(([tokens, userData]) => {
        setCsrf(tokens._csrf);
        setFormId(tokens._formId);
        setUsers(userData.users);
      })
      .catch((err) => setError((err as Error).message));
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await createTask({
        title,
        description,
        priority,
        assigneeId: assigneeId ? parseInt(assigneeId) : null,
        projectCode: projectCode || null,
        _csrf: csrf,
        _formId: formId,
      });
      addToast('Task created');
      navigate('/tasks');
    } catch (err) {
      setError((err as Error).message);
      addToast((err as Error).message, 'error');
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
    <>
      <Navbar />
      <main className="page-container">
        <h1>Create Task</h1>

        {error && <div className="error-message">{error}</div>}

        <form onSubmit={handleSubmit} className="form-card">
          {/* Hidden CSRF tokens */}
          <input type="hidden" name="_csrf" value={csrf} />
          <input type="hidden" name="_formId" value={formId} />

          <div className="form-group">
            <label htmlFor="title">Title *</label>
            <input
              id="title"
              type="text"
              name="title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="description">Description</label>
            <textarea
              id="description"
              name="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={4}
            />
          </div>

          <div className="form-row">
            <div className="form-group">
              <label htmlFor="priority">Priority</label>
              <select id="priority" name="priority" value={priority} onChange={(e) => setPriority(e.target.value)}>
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="urgent">Urgent</option>
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="assignee">Assignee</label>
              <select id="assignee" name="assigneeId" value={assigneeId} onChange={(e) => setAssigneeId(e.target.value)}>
                <option value="">Unassigned</option>
                {users.map((u) => (
                  <option key={u.id} value={u.id}>{u.display_name}</option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="projectCode">Project Code</label>
              <input
                id="projectCode"
                type="text"
                name="projectCode"
                value={projectCode}
                onChange={(e) => setProjectCode(e.target.value)}
                placeholder="PRJ-001"
              />
            </div>
          </div>

          <button type="submit" className="btn-primary" disabled={loading || !csrf}>
            {loading ? 'Creating...' : 'Create Task'}
          </button>
        </form>
      </main>
    </>
  );
}
