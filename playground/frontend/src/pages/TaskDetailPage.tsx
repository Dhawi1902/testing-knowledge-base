import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useToast } from '../components/Toast';
import ConfirmDialog from '../components/ConfirmDialog';
import Navbar from '../components/Navbar';
import {
  getTask,
  getTaskAttachments,
  getTaskSchedules,
  getUsers,
  addComment,
  uploadAttachment,
  deleteTask,
  updateTask,
  submitForReview,
  getCsrfTokens,
} from '../services/api';

export default function TaskDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { addToast } = useToast();
  const taskId = parseInt(id || '0');

  const [task, setTask] = useState<Record<string, any> | null>(null);
  const [attachments, setAttachments] = useState<any[]>([]);
  const [schedules, setSchedules] = useState<any[]>([]);
  const [users, setUsers] = useState<any[]>([]);
  const [error, setError] = useState('');

  // Comment form
  const [comment, setComment] = useState('');
  const [commentLoading, setCommentLoading] = useState(false);

  // File upload
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadLoading, setUploadLoading] = useState(false);

  // Delete confirmation
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleteLoading, setDeleteLoading] = useState(false);

  const user = JSON.parse(localStorage.getItem('user') || '{}');

  useEffect(() => {
    if (!taskId) return;
    // 4 parallel AJAX calls — TC01 tests this pattern
    Promise.all([
      getTask(taskId),
      getTaskAttachments(taskId),
      getTaskSchedules(taskId),
      getUsers(),
    ])
      .then(([taskData, attachData, schedData, userData]) => {
        setTask(taskData);
        setAttachments(attachData.attachments || []);
        setSchedules(schedData.schedules || []);
        setUsers(userData.users || []);
      })
      .catch((err) => setError((err as Error).message));
  }, [taskId]);

  async function handleAddComment(e: React.FormEvent) {
    e.preventDefault();
    if (!comment.trim() || !task) return;
    setCommentLoading(true);
    try {
      const csrf = await getCsrfTokens();
      const newComment = await addComment(taskId, comment, csrf._csrf, csrf._formId);
      setTask({
        ...task,
        comments: [...(task.comments || []), { ...newComment, author_name: user.displayName }],
      });
      setComment('');
      addToast('Comment added');
    } catch (err) {
      addToast((err as Error).message, 'error');
    } finally {
      setCommentLoading(false);
    }
  }

  async function handleUpload() {
    if (!selectedFile || !task) return;
    setUploadLoading(true);
    try {
      const csrf = await getCsrfTokens();
      const result = await uploadAttachment(taskId, selectedFile, csrf._csrf, csrf._formId);
      setAttachments([result, ...attachments]);
      setSelectedFile(null);
      addToast('File uploaded');
    } catch (err) {
      addToast((err as Error).message, 'error');
    } finally {
      setUploadLoading(false);
    }
  }

  async function handleDelete() {
    setDeleteLoading(true);
    try {
      const csrf = await getCsrfTokens();
      await deleteTask(taskId, csrf._csrf, csrf._formId);
      addToast('Task deleted');
      navigate('/tasks');
    } catch (err) {
      addToast((err as Error).message, 'error');
    } finally {
      setDeleteLoading(false);
      setShowDeleteConfirm(false);
    }
  }

  async function handleSubmitForReview() {
    if (!task) return;
    try {
      const csrf = await getCsrfTokens();
      const updated = await submitForReview(taskId, csrf._csrf, csrf._formId);
      setTask({ ...task, status: updated.status || 'pending_review' });
      addToast('Submitted for review');
    } catch (err) {
      addToast((err as Error).message, 'error');
    }
  }

  if (error) {
    return (
      <>
        <Navbar />
        <main className="page-container">
          <div className="error-message">{error}</div>
        </main>
      </>
    );
  }

  if (!task) {
    return (
      <>
        <Navbar />
        <main className="page-container"><p>Loading...</p></main>
      </>
    );
  }

  const canEdit = user.id === task.creator_id || user.role === 'manager';
  const canSubmitReview = ['open', 'in_progress', 'rejected'].includes(task.status) && user.id === task.creator_id;

  return (
    <>
      <Navbar />
      <main className="page-container">
        <div className="detail-header">
          <div>
            <h1>{task.title}</h1>
            <span className={`badge badge-${task.status}`}>{task.status.replaceAll('_', ' ')}</span>
            <span className={`badge badge-priority-${task.priority}`} style={{ marginLeft: '0.5rem' }}>{task.priority}</span>
          </div>
          <div className="detail-actions">
            {canSubmitReview && (
              <button onClick={handleSubmitForReview} className="btn-primary" style={{ width: 'auto' }}>
                Submit for Review
              </button>
            )}
            <Link to={`/tasks/${taskId}/schedule`} className="btn-secondary" style={{ textDecoration: 'none', padding: '0.5rem 1rem' }}>
              Schedule
            </Link>
            {canEdit && (
              <button onClick={() => setShowDeleteConfirm(true)} className="btn-danger" data-testid="delete-task-btn">
                Delete
              </button>
            )}
          </div>
        </div>

        <div className="detail-grid">
          {/* Task info */}
          <section className="detail-card">
            <h2>Details</h2>
            <dl className="detail-list">
              <dt>Project</dt><dd>{task.project_code || '—'}</dd>
              <dt>Assignee</dt><dd>{task.assignee_name || 'Unassigned'}</dd>
              <dt>Creator</dt><dd>{task.creator_name}</dd>
              <dt>Created</dt><dd>{new Date(task.created_at).toLocaleDateString()}</dd>
              <dt>Updated</dt><dd>{new Date(task.updated_at).toLocaleDateString()}</dd>
            </dl>
            {task.description && <p className="detail-description">{task.description}</p>}
          </section>

          {/* Attachments */}
          <section className="detail-card">
            <h2>Attachments ({attachments.length})</h2>
            {attachments.length > 0 && (
              <ul className="attachment-list">
                {attachments.map((att: any) => (
                  <li key={att.id}>
                    <a href={att.downloadUrl} target="_blank" rel="noopener noreferrer">
                      {att.original_name}
                    </a>
                    <span className="attachment-meta">
                      {(att.size_bytes / 1024).toFixed(1)} KB — {att.uploader_name}
                    </span>
                  </li>
                ))}
              </ul>
            )}
            <div className="upload-row">
              <input
                type="file"
                onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                data-testid="file-input"
              />
              <button
                onClick={handleUpload}
                disabled={!selectedFile || uploadLoading}
                className="btn-secondary"
              >
                {uploadLoading ? 'Uploading...' : 'Upload'}
              </button>
            </div>
          </section>

          {/* Schedules */}
          <section className="detail-card">
            <h2>Schedules ({schedules.length})</h2>
            {schedules.length > 0 ? (
              <table className="mini-table">
                <thead>
                  <tr><th>Date</th><th>Time</th><th>Dept</th><th>Status</th></tr>
                </thead>
                <tbody>
                  {schedules.map((s: any) => (
                    <tr key={s.id}>
                      <td>{s.slot_date}</td>
                      <td>{s.slot_time}</td>
                      <td>{s.department || '—'}</td>
                      <td><span className={`badge badge-${s.status}`}>{s.status.replaceAll('_', ' ')}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="empty-state">No schedules yet</p>
            )}
          </section>
        </div>

        {/* Comments */}
        <section className="detail-card" style={{ marginTop: '1.5rem' }}>
          <h2>Comments ({task.comments?.length || 0})</h2>
          {task.comments?.length > 0 && (
            <div className="comment-list">
              {task.comments.map((c: any) => (
                <div key={c.id} className="comment-item">
                  <div className="comment-header">
                    <strong>{c.author_name}</strong>
                    <span>{new Date(c.created_at).toLocaleString()}</span>
                  </div>
                  <p>{c.content}</p>
                </div>
              ))}
            </div>
          )}
          <form onSubmit={handleAddComment} className="comment-form">
            <textarea
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder="Add a comment..."
              rows={3}
              required
              data-testid="comment-input"
            />
            <button type="submit" disabled={commentLoading || !comment.trim()} className="btn-primary" style={{ width: 'auto' }}>
              {commentLoading ? 'Posting...' : 'Add Comment'}
            </button>
          </form>
        </section>
      </main>

      <ConfirmDialog
        open={showDeleteConfirm}
        title="Delete Task"
        message={`Are you sure you want to delete "${task.title}"? This action cannot be undone.`}
        confirmLabel="Delete"
        onConfirm={handleDelete}
        onCancel={() => setShowDeleteConfirm(false)}
      />
    </>
  );
}
