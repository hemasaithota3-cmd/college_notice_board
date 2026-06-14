-- ═══════════════════════════════════════════════════════════════
--  Smart College Notice Board - Database Schema
-- ═══════════════════════════════════════════════════════════════

CREATE DATABASE IF NOT EXISTS college_noticeboard
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE college_noticeboard;

-- ── Categories ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS categories (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(100) NOT NULL UNIQUE,
    icon        VARCHAR(50)  DEFAULT 'bi-tag',
    color       VARCHAR(20)  DEFAULT '#1a56db',
    description TEXT,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT IGNORE INTO categories (name, icon, color, description) VALUES
('Academic',      'bi-book',         '#1a56db', 'Academic schedules, syllabus, timetables'),
('Placement',     'bi-briefcase',    '#0e9f6e', 'Job & internship placements, campus drives'),
('Examination',   'bi-pencil-square','#d97706', 'Exam dates, hall tickets, results'),
('Events',        'bi-calendar-event','#7e3af2','College fests, seminars, workshops'),
('Scholarships',  'bi-award',        '#e02424', 'Scholarship announcements and deadlines'),
('Circulars',     'bi-megaphone',    '#6b7280', 'General circulars and administrative notices');

-- ── Users ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    full_name    VARCHAR(150) NOT NULL,
    email        VARCHAR(200) NOT NULL UNIQUE,
    password     VARCHAR(255) NOT NULL,
    role         ENUM('admin','faculty','student') NOT NULL DEFAULT 'student',
    department   VARCHAR(100),
    avatar       VARCHAR(255),
    phone        VARCHAR(20),
    roll_no      VARCHAR(50),
    is_active    TINYINT(1)   DEFAULT 1,
    created_at   TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at   TIMESTAMP    DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_email (email),
    INDEX idx_role  (role)
);

-- Default passwords (plain text - no hashing)
-- Admin password:   Admin@123
-- Faculty password: Faculty@123
-- Student password: Student@123
INSERT IGNORE INTO users (full_name, email, password, role, department) VALUES
('Super Admin',      'admin@college.edu',   'Admin@123',   'admin',   'Administration'),
('Dr. Ramesh Kumar', 'faculty@college.edu', 'Faculty@123', 'faculty', 'Computer Science'),
('Priya Sharma',     'student@college.edu', 'Student@123', 'student', 'Computer Science');

-- ── Notices ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS notices (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    title        VARCHAR(300)  NOT NULL,
    description  TEXT          NOT NULL,
    category_id  INT           NOT NULL,
    user_id      INT           NOT NULL,
    priority     ENUM('low','normal','high','urgent') DEFAULT 'normal',
    attachment   VARCHAR(500),
    attach_type  ENUM('pdf','image') DEFAULT NULL,
    expiry_date  DATE          DEFAULT NULL,
    views        INT           DEFAULT 0,
    is_archived  TINYINT(1)    DEFAULT 0,
    created_at   TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,
    updated_at   TIMESTAMP     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE RESTRICT,
    FOREIGN KEY (user_id)     REFERENCES users(id)      ON DELETE CASCADE,
    INDEX idx_category   (category_id),
    INDEX idx_user       (user_id),
    INDEX idx_priority   (priority),
    INDEX idx_expiry     (expiry_date),
    INDEX idx_archived   (is_archived),
    FULLTEXT idx_search  (title, description)
);

-- Sample notices
INSERT IGNORE INTO notices (title, description, category_id, user_id, priority, expiry_date) VALUES
('End Semester Examination Schedule - 2024',
 'The end semester examinations for all branches will commence from 15th December 2024. Students are advised to download their hall tickets from the student portal. Examination will be held in the college examination hall from 9:00 AM to 12:00 PM. No electronic devices are permitted.',
 3, 1, 'urgent', DATE_ADD(CURDATE(), INTERVAL 30 DAY)),

('Campus Placement Drive - TCS & Infosys',
 'TCS and Infosys will be conducting their campus placement drive on 20th November 2024. Eligible students (7.5+ CGPA, no active backlogs) should register on the placement portal by 15th November. Dress code: Formal attire. Carry original certificates and 5 passport photos.',
 2, 2, 'high', DATE_ADD(CURDATE(), INTERVAL 15 DAY)),

('Annual Technical Fest - TECHFEST 2024',
 'The Annual Technical Fest TECHFEST 2024 will be held on 25-27 November 2024. Events include Hackathon, Paper Presentation, Coding Contest, Robotics, and Cultural Programs. Registration open till 20th November. Prizes worth ₹5,00,000!',
 4, 2, 'high', DATE_ADD(CURDATE(), INTERVAL 20 DAY)),

('Merit Scholarship Applications Open',
 'Applications are invited for the Government Merit Scholarship 2024-25. Students with 85%+ marks in the previous year and family income below ₹6 lakhs per annum are eligible. Submit applications with required documents to the scholarship office by 30th November 2024.',
 5, 1, 'high', DATE_ADD(CURDATE(), INTERVAL 25 DAY)),

('Academic Calendar 2024-25 Released',
 'The Academic Calendar for the year 2024-25 has been released. It includes semester dates, holiday list, examination schedule, and important deadlines. Students and faculty can download the calendar from the admin office or the college website.',
 1, 1, 'normal', NULL),

('Library Timing Changes',
 'The college library will now be open from 7:00 AM to 9:00 PM on all working days and 9:00 AM to 5:00 PM on Saturdays. Sunday hours remain 10:00 AM to 4:00 PM. All students must carry their ID cards for entry.',
 6, 1, 'normal', NULL);

-- ── Notifications ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS notifications (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    user_id    INT           NOT NULL,
    notice_id  INT           DEFAULT NULL,
    title      VARCHAR(200)  NOT NULL,
    message    TEXT,
    is_read    TINYINT(1)    DEFAULT 0,
    created_at TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id)   REFERENCES users(id)   ON DELETE CASCADE,
    FOREIGN KEY (notice_id) REFERENCES notices(id) ON DELETE SET NULL,
    INDEX idx_user_read (user_id, is_read)
);

-- ── Activity Logs ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS activity_logs (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    user_id    INT           NOT NULL,
    action     VARCHAR(100)  NOT NULL,
    details    TEXT,
    ip_address VARCHAR(45),
    created_at TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user   (user_id),
    INDEX idx_action (action)
);
