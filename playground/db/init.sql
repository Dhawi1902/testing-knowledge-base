-- TaskFlow Database Schema
-- This file runs automatically on first PostgreSQL boot via docker-entrypoint-initdb.d

-- ============================================================
-- EXTENSIONS
-- ============================================================
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ============================================================
-- TABLES
-- ============================================================

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'staff' CHECK (role IN ('staff', 'manager', 'admin')),
    is_verified BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE tasks (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(30) NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'in_progress', 'completed', 'pending_review', 'approved', 'rejected')),
    priority VARCHAR(10) NOT NULL DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'urgent')),
    project_code VARCHAR(20),
    assignee_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    creator_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE comments (
    id SERIAL PRIMARY KEY,
    task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE refresh_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE attachments (
    id SERIAL PRIMARY KEY,
    task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    original_name VARCHAR(255) NOT NULL,
    stored_name VARCHAR(255) NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    size_bytes INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE schedules (
    id SERIAL PRIMARY KEY,
    task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    confirmation_id VARCHAR(100) UNIQUE NOT NULL,
    confirm_hash VARCHAR(255) UNIQUE,
    slot_date DATE NOT NULL,
    slot_time VARCHAR(20) NOT NULL,
    department VARCHAR(100),
    priority VARCHAR(10),
    notes TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'confirmed', 'cancelled')),
    payload JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE verification_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(255) UNIQUE NOT NULL,
    type VARCHAR(20) NOT NULL CHECK (type IN ('email_verify', 'password_reset')),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    used BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE export_jobs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_id VARCHAR(100) UNIQUE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'processing' CHECK (status IN ('processing', 'completed', 'failed')),
    total_steps INTEGER NOT NULL DEFAULT 5,
    current_step INTEGER NOT NULL DEFAULT 0,
    download_hash VARCHAR(255) UNIQUE,
    filters JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE admin_sessions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) UNIQUE NOT NULL,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_assignee ON tasks(assignee_id);
CREATE INDEX idx_tasks_creator ON tasks(creator_id);
CREATE INDEX idx_comments_task ON comments(task_id);
CREATE INDEX idx_refresh_tokens_user ON refresh_tokens(user_id);
CREATE INDEX idx_refresh_tokens_hash ON refresh_tokens(token_hash);
CREATE INDEX idx_attachments_task ON attachments(task_id);
CREATE INDEX idx_schedules_task ON schedules(task_id);
CREATE INDEX idx_schedules_confirmation ON schedules(confirmation_id);
CREATE INDEX idx_verification_tokens_token ON verification_tokens(token);
CREATE INDEX idx_export_jobs_job ON export_jobs(job_id);
CREATE INDEX idx_admin_sessions_session ON admin_sessions(session_id);

-- ============================================================
-- SEED DATA
-- ============================================================

-- Users: passwords are bcrypt-hashed using pgcrypto
-- Staff: user01-user15 (password01-password15)
-- Manager: user16-user19 (password16-password19)
-- Manager (admin-level JWT): user20 (password20)
-- Admin (cookie session): admin@taskflow.local (admin123)

INSERT INTO users (email, password_hash, display_name, role, is_verified) VALUES
    ('user01@taskflow.local', crypt('password01', gen_salt('bf', 10)), 'Alice Johnson', 'staff', true),
    ('user02@taskflow.local', crypt('password02', gen_salt('bf', 10)), 'Bob Smith', 'staff', true),
    ('user03@taskflow.local', crypt('password03', gen_salt('bf', 10)), 'Charlie Brown', 'staff', true),
    ('user04@taskflow.local', crypt('password04', gen_salt('bf', 10)), 'Diana Prince', 'staff', true),
    ('user05@taskflow.local', crypt('password05', gen_salt('bf', 10)), 'Edward Norton', 'staff', true),
    ('user06@taskflow.local', crypt('password06', gen_salt('bf', 10)), 'Fiona Apple', 'staff', true),
    ('user07@taskflow.local', crypt('password07', gen_salt('bf', 10)), 'George Miller', 'staff', true),
    ('user08@taskflow.local', crypt('password08', gen_salt('bf', 10)), 'Hannah Lee', 'staff', true),
    ('user09@taskflow.local', crypt('password09', gen_salt('bf', 10)), 'Ivan Petrov', 'staff', true),
    ('user10@taskflow.local', crypt('password10', gen_salt('bf', 10)), 'Julia Chen', 'staff', true),
    ('user11@taskflow.local', crypt('password11', gen_salt('bf', 10)), 'Kevin Park', 'staff', true),
    ('user12@taskflow.local', crypt('password12', gen_salt('bf', 10)), 'Laura Martinez', 'staff', true),
    ('user13@taskflow.local', crypt('password13', gen_salt('bf', 10)), 'Michael Wong', 'staff', true),
    ('user14@taskflow.local', crypt('password14', gen_salt('bf', 10)), 'Nina Patel', 'staff', true),
    ('user15@taskflow.local', crypt('password15', gen_salt('bf', 10)), 'Oscar Rivera', 'staff', true),
    ('user16@taskflow.local', crypt('password16', gen_salt('bf', 10)), 'Patricia Kim', 'manager', true),
    ('user17@taskflow.local', crypt('password17', gen_salt('bf', 10)), 'Quentin Blake', 'manager', true),
    ('user18@taskflow.local', crypt('password18', gen_salt('bf', 10)), 'Rachel Green', 'manager', true),
    ('user19@taskflow.local', crypt('password19', gen_salt('bf', 10)), 'Samuel Jackson', 'manager', true),
    ('user20@taskflow.local', crypt('password20', gen_salt('bf', 10)), 'Tina Turner', 'manager', true),
    ('admin@taskflow.local', crypt('admin123', gen_salt('bf', 10)), 'System Admin', 'admin', true);

-- Tasks: 200 tasks with mixed statuses, assigned to various users
-- Project codes: PRJ-001 through PRJ-010
DO $$
DECLARE
    i INTEGER;
    statuses TEXT[] := ARRAY['open', 'in_progress', 'completed', 'pending_review', 'approved', 'rejected'];
    priorities TEXT[] := ARRAY['low', 'medium', 'high', 'urgent'];
    project_codes TEXT[] := ARRAY['PRJ-001', 'PRJ-002', 'PRJ-003', 'PRJ-004', 'PRJ-005', 'PRJ-006', 'PRJ-007', 'PRJ-008', 'PRJ-009', 'PRJ-010'];
    task_titles TEXT[] := ARRAY[
        'Update user authentication flow',
        'Fix pagination on task list',
        'Add email notification system',
        'Refactor database queries',
        'Create API documentation',
        'Implement file upload feature',
        'Design dashboard layout',
        'Write unit tests for auth module',
        'Optimize image compression',
        'Set up CI/CD pipeline',
        'Review security vulnerabilities',
        'Add search functionality',
        'Update dependencies to latest versions',
        'Create user onboarding flow',
        'Fix mobile responsive issues',
        'Add dark mode support',
        'Implement rate limiting',
        'Create backup automation',
        'Add activity logging',
        'Improve error handling'
    ];
    status_val TEXT;
    priority_val TEXT;
    assignee INTEGER;
    creator INTEGER;
BEGIN
    FOR i IN 1..200 LOOP
        status_val := statuses[1 + (i % array_length(statuses, 1))];
        priority_val := priorities[1 + (i % array_length(priorities, 1))];
        assignee := 1 + (i % 20);
        creator := 1 + ((i + 7) % 20);

        INSERT INTO tasks (title, description, status, priority, project_code, assignee_id, creator_id, created_at)
        VALUES (
            task_titles[1 + (i % array_length(task_titles, 1))] || ' #' || i,
            'Description for task #' || i || '. This task involves ' ||
            LOWER(task_titles[1 + (i % array_length(task_titles, 1))]) || '.',
            status_val,
            priority_val,
            project_codes[1 + (i % array_length(project_codes, 1))],
            assignee,
            creator,
            NOW() - (interval '1 day' * (200 - i))
        );
    END LOOP;
END $$;

-- Comments: 500 comments distributed across tasks
DO $$
DECLARE
    i INTEGER;
    comment_templates TEXT[] := ARRAY[
        'I''ve started working on this.',
        'Can we discuss the approach for this?',
        'Updated the implementation based on feedback.',
        'This needs more testing before we proceed.',
        'Looks good to me, ready for review.',
        'Found a potential issue with this approach.',
        'Dependencies have been updated.',
        'Added error handling for edge cases.',
        'The design has been approved by the team.',
        'Please check the latest changes.'
    ];
BEGIN
    FOR i IN 1..500 LOOP
        INSERT INTO comments (task_id, user_id, content, created_at)
        VALUES (
            1 + (i % 200),
            1 + (i % 20),
            comment_templates[1 + (i % array_length(comment_templates, 1))],
            NOW() - (interval '1 hour' * (500 - i))
        );
    END LOOP;
END $$;
