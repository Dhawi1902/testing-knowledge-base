const API_BASE = '/api';

// ─── Core Request Helpers ────────────────────────────────────────────

interface ApiOptions {
  method?: string;
  body?: Record<string, unknown>;
}

async function request<T>(endpoint: string, options: ApiOptions = {}): Promise<T> {
  const { method = 'GET', body } = options;
  const headers: Record<string, string> = {
    'Accept': 'application/json',
    'X-Requested-With': 'XMLHttpRequest',
  };
  if (body) {
    headers['Content-Type'] = 'application/json';
  }
  const token = localStorage.getItem('accessToken');
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Request failed' }));
    throw new Error(error.error || `HTTP ${response.status}`);
  }
  return response.json();
}

async function uploadFile<T>(endpoint: string, formData: FormData): Promise<T> {
  const headers: Record<string, string> = {
    'Accept': 'application/json',
    'X-Requested-With': 'XMLHttpRequest',
  };
  const token = localStorage.getItem('accessToken');
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    method: 'POST',
    headers,
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Upload failed' }));
    throw new Error(error.error || `HTTP ${response.status}`);
  }
  return response.json();
}

async function requestText(endpoint: string): Promise<string> {
  const headers: Record<string, string> = {
    'Accept': 'text/html',
    'X-Requested-With': 'XMLHttpRequest',
  };
  const token = localStorage.getItem('accessToken');
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE}${endpoint}`, { headers });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return response.text();
}

async function adminRequest<T>(path: string, options: { method?: string; body?: Record<string, unknown> } = {}): Promise<T> {
  const headers: Record<string, string> = {
    'Accept': 'application/json',
  };
  if (options.body) {
    headers['Content-Type'] = 'application/json';
  }

  const response = await fetch(path, {
    method: options.method || 'GET',
    headers,
    credentials: 'same-origin',
    body: options.body ? JSON.stringify(options.body) : undefined,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Request failed' }));
    throw new Error(error.error || `HTTP ${response.status}`);
  }
  return response.json();
}

// ─── Auth ────────────────────────────────────────────────────────────

export function getCsrfTokens() {
  return request<{ _csrf: string; _formId: string }>('/auth/csrf');
}

export function login(email: string, password: string, _csrf: string, _formId: string) {
  return request<{
    accessToken: string;
    refreshToken: string;
    user: { id: number; email: string; displayName: string; role: string };
  }>('/auth/login', { method: 'POST', body: { email, password, _csrf, _formId } });
}

export function register(email: string, password: string, displayName: string, _csrf: string, _formId: string) {
  return request<{
    message: string;
    userId: number;
    verificationUrl: string;
  }>('/auth/register', { method: 'POST', body: { email, password, displayName, _csrf, _formId } });
}

export function forgotPassword(email: string, _csrf: string, _formId: string) {
  return request<{
    message: string;
    resetUrl?: string;
    _resetToken?: string;
  }>('/auth/forgot-password', { method: 'POST', body: { email, _csrf, _formId } });
}

// ─── Tasks ───────────────────────────────────────────────────────────

export function getTasks(params: Record<string, string> = {}) {
  const query = new URLSearchParams(params).toString();
  return request<{
    tasks: Array<Record<string, any>>;
    pagination: { page: number; limit: number; total: number; totalPages: number };
  }>(`/tasks${query ? `?${query}` : ''}`);
}

export function getTask(id: number) {
  return request<Record<string, any>>(`/tasks/${id}`);
}

export function createTask(data: Record<string, unknown>) {
  return request<Record<string, any>>('/tasks', { method: 'POST', body: data });
}

export function updateTask(id: number, data: Record<string, unknown>) {
  return request<Record<string, any>>(`/tasks/${id}`, { method: 'PUT', body: data });
}

export function deleteTask(id: number, _csrf: string, _formId: string) {
  return request<{ message: string }>(`/tasks/${id}`, { method: 'DELETE', body: { _csrf, _formId } });
}

// ─── Task Attachments ────────────────────────────────────────────────

export function getTaskAttachments(taskId: number) {
  return request<{
    attachments: Array<{
      id: number;
      original_name: string;
      mime_type: string;
      size_bytes: number;
      uploader_name: string;
      created_at: string;
      downloadUrl: string;
    }>;
  }>(`/tasks/${taskId}/attachments`);
}

export function uploadAttachment(taskId: number, file: File, _csrf: string, _formId: string) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('_csrf', _csrf);
  formData.append('_formId', _formId);
  return uploadFile<Record<string, any>>(`/tasks/${taskId}/attachments`, formData);
}

// ─── Task Comments ───────────────────────────────────────────────────

export function addComment(taskId: number, content: string, _csrf: string, _formId: string) {
  return request<Record<string, any>>(`/tasks/${taskId}/comments`, {
    method: 'POST',
    body: { content, _csrf, _formId },
  });
}

// ─── Task Workflow ───────────────────────────────────────────────────

export function submitForReview(taskId: number, _csrf: string, _formId: string) {
  return request<Record<string, any>>(`/tasks/${taskId}/submit-review`, {
    method: 'PUT',
    body: { _csrf, _formId },
  });
}

export function approveTask(taskId: number, _csrf: string, _formId: string, remarks?: string) {
  return request<Record<string, any>>(`/tasks/${taskId}/approve`, {
    method: 'PUT',
    body: { _csrf, _formId, ...(remarks ? { remarks } : {}) },
  });
}

export function rejectTask(taskId: number, remarks: string, _csrf: string, _formId: string) {
  return request<Record<string, any>>(`/tasks/${taskId}/reject`, {
    method: 'PUT',
    body: { remarks, _csrf, _formId },
  });
}

// ─── Schedules ───────────────────────────────────────────────────────

export function getTaskSchedule(taskId: number) {
  return request<{
    taskId: number;
    taskTitle: string;
    projectCode: string;
    availableSlots: Array<{ date: string; times: string[] }>;
    departments: string[];
    _csrf: string;
    _formId: string;
  }>(`/tasks/${taskId}/schedule`);
}

export async function submitSchedule(taskId: number, data: Record<string, unknown>): Promise<{ confirmationId: string; reviewData: Record<string, any> }> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'X-Requested-With': 'XMLHttpRequest',
  };
  const token = localStorage.getItem('accessToken');
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE}/tasks/${taskId}/schedule`, {
    method: 'POST',
    headers,
    body: JSON.stringify(data),
    redirect: 'follow',
  });

  const urlMatch = response.url.match(/\/api\/schedules\/([^/]+)\/review/);
  const confirmationId = urlMatch?.[1] || '';

  if (response.ok) {
    const reviewData = await response.json();
    return { confirmationId, reviewData };
  }

  if (confirmationId) {
    const reviewData = await getScheduleReview(confirmationId);
    return { confirmationId, reviewData };
  }

  throw new Error('Schedule submission failed');
}

export function getTaskSchedules(taskId: number) {
  return request<{ schedules: Array<Record<string, any>> }>(`/tasks/${taskId}/schedules`);
}

export function getScheduleReview(confirmationId: string) {
  return request<Record<string, any>>(`/schedules/${confirmationId}/review`);
}

export function confirmSchedule(confirmationId: string, _csrf: string, _formId: string) {
  return request<{
    message: string;
    confirmationId: string;
    status: string;
    confirmUrl: string;
  }>(`/schedules/${confirmationId}/confirm`, {
    method: 'POST',
    body: { _csrf, _formId },
  });
}

// ─── Batch ───────────────────────────────────────────────────────────

export function getBatchEditData() {
  return request<{
    tasks: Array<Record<string, any>>;
    _csrf: string;
    _formId: string;
  }>('/tasks/batch-edit');
}

export function submitBatchUpdate(changesList: string, _csrf: string, _formId: string) {
  return request<{
    message: string;
    updated: Array<{ taskId: number; status: string }>;
    errors: Array<{ taskId: string; error: string }>;
  }>('/tasks/batch-update', {
    method: 'POST',
    body: { changesList, _csrf, _formId },
  });
}

// ─── Dashboard ───────────────────────────────────────────────────────

export function getDashboardStats() {
  return request<{
    byStatus: Array<{ status: string; count: string }>;
    total: number;
  }>('/dashboard/stats');
}

export function getDashboardRecent() {
  return request<{
    recentTasks: Array<Record<string, any>>;
    recentComments: Array<Record<string, any>>;
  }>('/dashboard/recent');
}

// ─── Users ───────────────────────────────────────────────────────────

export function getUsers() {
  return request<{ users: Array<{ id: number; email: string; display_name: string; role: string }> }>('/users');
}

export function getUserProfile() {
  return request<{
    id: number;
    email: string;
    display_name: string;
    role: string;
    is_verified: boolean;
    created_at: string;
    avatar_url?: string;
  }>('/users/me');
}

export function updateProfile(data: { displayName: string; _csrf: string; _formId: string }) {
  return request<Record<string, any>>('/users/me', { method: 'PUT', body: data });
}

export function uploadAvatar(file: File, _csrf: string, _formId: string) {
  const formData = new FormData();
  formData.append('avatar', file);
  formData.append('_csrf', _csrf);
  formData.append('_formId', _formId);
  return uploadFile<{ message: string; avatarUrl: string }>('/users/me/avatar', formData);
}

// ─── Admin (Cookie-Based Session) ────────────────────────────────────

export function adminGetLoginPage() {
  return adminRequest<{ message: string; _csrf: string; _formId: string }>('/admin/login');
}

export function adminLogin(email: string, password: string, _csrf: string, _formId: string) {
  return adminRequest<{
    message: string;
    user: { id: number; email: string; displayName: string; role: string };
  }>('/api/admin/auth/login', { method: 'POST', body: { email, password, _csrf, _formId } });
}

export function adminGetUsers() {
  return adminRequest<{ users: Array<Record<string, any>>; count: number }>('/api/admin/users');
}

export function adminGetStats() {
  return adminRequest<{
    users: number;
    tasks: number;
    comments: number;
    tasksByStatus: Array<{ status: string; count: string }>;
    usersByRole: Array<{ role: string; count: string }>;
  }>('/api/admin/stats');
}

export function adminLogout() {
  return adminRequest<{ message: string }>('/api/admin/auth/logout', { method: 'POST' });
}

// ─── Exports (Async Polling) ─────────────────────────────────────────

export function submitExport(filters: Record<string, unknown> = {}) {
  return request<{ jobId: string; statusUrl: string; message: string }>('/exports', {
    method: 'POST',
    body: filters,
  });
}

export function getExportStatus(jobId: string) {
  return requestText(`/exports/${jobId}/status`);
}

export function getExportDownload(hash: string) {
  return request<Record<string, any>>(`/exports/download/${hash}`);
}
