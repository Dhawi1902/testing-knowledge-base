import { lazy, Suspense } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';

// Lazy-loaded pages — only fetched when the route is visited
const LoginPage = lazy(() => import('./pages/LoginPage'));
const RegisterPage = lazy(() => import('./pages/RegisterPage'));
const DashboardPage = lazy(() => import('./pages/DashboardPage'));
const TaskListPage = lazy(() => import('./pages/TaskListPage'));
const TaskDetailPage = lazy(() => import('./pages/TaskDetailPage'));
const TaskCreatePage = lazy(() => import('./pages/TaskCreatePage'));
const ScheduleTaskPage = lazy(() => import('./pages/ScheduleTaskPage'));
const BatchEditPage = lazy(() => import('./pages/BatchEditPage'));
const ReviewQueuePage = lazy(() => import('./pages/ReviewQueuePage'));
const ProfilePage = lazy(() => import('./pages/ProfilePage'));
const AdminLoginPage = lazy(() => import('./pages/AdminLoginPage'));
const AdminDashboardPage = lazy(() => import('./pages/AdminDashboardPage'));

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem('accessToken');
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}

export default function App() {
  return (
    <Suspense fallback={<div className="page-container"><p>Loading...</p></div>}>
      <Routes>
        {/* Public routes */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />

        {/* Admin routes (cookie-based, no JWT) */}
        <Route path="/admin/login" element={<AdminLoginPage />} />
        <Route path="/admin/dashboard" element={<AdminDashboardPage />} />

        {/* Protected routes (JWT) */}
        <Route path="/dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
        <Route path="/tasks" element={<ProtectedRoute><TaskListPage /></ProtectedRoute>} />
        <Route path="/tasks/new" element={<ProtectedRoute><TaskCreatePage /></ProtectedRoute>} />
        <Route path="/tasks/batch-edit" element={<ProtectedRoute><BatchEditPage /></ProtectedRoute>} />
        <Route path="/tasks/review" element={<ProtectedRoute><ReviewQueuePage /></ProtectedRoute>} />
        <Route path="/tasks/:id/schedule" element={<ProtectedRoute><ScheduleTaskPage /></ProtectedRoute>} />
        <Route path="/tasks/:id" element={<ProtectedRoute><TaskDetailPage /></ProtectedRoute>} />
        <Route path="/profile" element={<ProtectedRoute><ProfilePage /></ProtectedRoute>} />

        {/* Redirects */}
        <Route path="/" element={<Navigate to="/login" replace />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </Suspense>
  );
}
