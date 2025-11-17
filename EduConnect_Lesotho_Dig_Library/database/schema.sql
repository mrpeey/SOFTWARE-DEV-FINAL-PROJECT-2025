-- Butha-Buthe Digital Library Database Schema
-- Designed for resource-constrained environments with offline capabilities

CREATE DATABASE IF NOT EXISTS butha_buthe_library;
USE butha_buthe_library;

-- User roles table
CREATE TABLE user_roles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    role_name VARCHAR(50) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert default roles
INSERT INTO user_roles (role_name, description) VALUES
('admin', 'System administrator with full access'),
('librarian', 'Library staff with management privileges'),
('student', 'Student user with borrowing privileges'),
('public', 'General public user with limited access'),
('researcher', 'Researcher with extended access to academic resources');

-- Users table
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    phone_number VARCHAR(20),
    address TEXT,
    district VARCHAR(50) DEFAULT 'Butha-Buthe',
    role_id INT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    email_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_login TIMESTAMP NULL,
    FOREIGN KEY (role_id) REFERENCES user_roles(id),
    INDEX idx_username (username),
    INDEX idx_email (email),
    INDEX idx_district (district)
);

-- Categories table for organizing books and resources
CREATE TABLE categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    parent_id INT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_id) REFERENCES categories(id) ON DELETE SET NULL,
    INDEX idx_parent (parent_id)
);

-- Insert default categories
INSERT INTO categories (name, description) VALUES
('Academic', 'Academic and educational resources'),
('Literature', 'Fiction and literary works'),
('Science & Technology', 'Science, technology and engineering'),
('History & Culture', 'Historical and cultural materials'),
('Health & Medicine', 'Medical and health resources'),
('Agriculture', 'Agricultural and farming resources'),
('Business & Economics', 'Business and economic materials'),
('Government & Law', 'Legal and government documents'),
('Digital Literacy', 'Computer and digital skills resources'),
('Local Resources', 'Local Lesotho and community materials');

-- Books table
CREATE TABLE books (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    author VARCHAR(300) NOT NULL,
    isbn VARCHAR(20) UNIQUE,
    publisher VARCHAR(200),
    publication_year YEAR,
    edition VARCHAR(50),
    pages INT,
    language VARCHAR(50) DEFAULT 'English',
    description TEXT,
    category_id INT NOT NULL,
    is_digital BOOLEAN DEFAULT FALSE,
    file_path VARCHAR(500) NULL,
    file_size BIGINT NULL, -- in bytes
    file_format VARCHAR(20) NULL, -- PDF, EPUB, etc.
    cover_image VARCHAR(500) NULL,
    total_copies INT DEFAULT 1,
    available_copies INT DEFAULT 1,
    is_active BOOLEAN DEFAULT TRUE,
    is_featured BOOLEAN DEFAULT FALSE,
    download_count INT DEFAULT 0,
    view_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_by INT NOT NULL,
    FOREIGN KEY (category_id) REFERENCES categories(id),
    FOREIGN KEY (created_by) REFERENCES users(id),
    INDEX idx_title (title),
    INDEX idx_author (author),
    INDEX idx_isbn (isbn),
    INDEX idx_category (category_id),
    INDEX idx_is_digital (is_digital),
    FULLTEXT idx_search (title, author, description)
);

-- Borrowing transactions
CREATE TABLE borrowing_transactions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    book_id INT NOT NULL,
    borrowed_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    due_date DATE NOT NULL,
    returned_date TIMESTAMP NULL,
    status ENUM('borrowed', 'returned', 'overdue', 'renewed') DEFAULT 'borrowed',
    renewal_count INT DEFAULT 0,
    fine_amount DECIMAL(10,2) DEFAULT 0.00,
    fine_paid BOOLEAN DEFAULT FALSE,
    librarian_id INT NOT NULL,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (book_id) REFERENCES books(id),
    FOREIGN KEY (librarian_id) REFERENCES users(id),
    INDEX idx_user_status (user_id, status),
    INDEX idx_book_status (book_id, status),
    INDEX idx_due_date (due_date),
    INDEX idx_status (status)
);

-- Digital downloads tracking
CREATE TABLE digital_downloads (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    book_id INT NOT NULL,
    download_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address VARCHAR(45),
    user_agent TEXT,
    file_size BIGINT,
    download_complete BOOLEAN DEFAULT TRUE,
    offline_access_granted BOOLEAN DEFAULT FALSE,
    offline_expiry_date DATE NULL,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (book_id) REFERENCES books(id),
    INDEX idx_user_book (user_id, book_id),
    INDEX idx_download_date (download_date)
);

-- Offline access tokens for low-bandwidth environments
CREATE TABLE offline_tokens (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    token_hash VARCHAR(255) NOT NULL UNIQUE,
    resources_included JSON, -- List of book IDs accessible offline
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expiry_date TIMESTAMP NOT NULL,
    last_sync TIMESTAMP NULL,
    is_active BOOLEAN DEFAULT TRUE,
    device_info TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id),
    INDEX idx_token_hash (token_hash),
    INDEX idx_user_active (user_id, is_active),
    INDEX idx_expiry (expiry_date)
);

-- Reading sessions for analytics
CREATE TABLE reading_sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    book_id INT NOT NULL,
    session_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    session_end TIMESTAMP NULL,
    pages_read INT DEFAULT 0,
    reading_progress DECIMAL(5,2) DEFAULT 0.00, -- percentage
    device_type VARCHAR(50),
    is_offline BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (book_id) REFERENCES books(id),
    INDEX idx_user_book (user_id, book_id),
    INDEX idx_session_date (session_start)
);

-- System notifications
CREATE TABLE notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NULL, -- NULL for system-wide notifications
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    type ENUM('info', 'warning', 'success', 'error') DEFAULT 'info',
    is_read BOOLEAN DEFAULT FALSE,
    is_system_wide BOOLEAN DEFAULT FALSE,
    priority INT DEFAULT 1, -- 1=low, 2=medium, 3=high
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_read (user_id, is_read),
    INDEX idx_system_wide (is_system_wide),
    INDEX idx_created_at (created_at)
);

-- System settings for configuration
CREATE TABLE system_settings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    setting_key VARCHAR(100) NOT NULL UNIQUE,
    setting_value TEXT,
    description TEXT,
    is_public BOOLEAN DEFAULT FALSE, -- Whether setting can be viewed by non-admins
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    updated_by INT NOT NULL,
    FOREIGN KEY (updated_by) REFERENCES users(id),
    INDEX idx_key (setting_key)
);

-- Insert default system settings
INSERT INTO system_settings (setting_key, setting_value, description, is_public, updated_by) VALUES
('library_name', 'Butha-Buthe Digital Library', 'Name of the library system', TRUE, 1),
('max_borrowing_days', '14', 'Maximum borrowing period in days', TRUE, 1),
('max_renewals', '2', 'Maximum number of renewals allowed', TRUE, 1),
('fine_per_day', '1.00', 'Fine amount per day for overdue books (in local currency)', TRUE, 1),
('max_books_per_user', '5', 'Maximum books a user can borrow simultaneously', TRUE, 1),
('offline_access_days', '30', 'Days offline access is valid', TRUE, 1),
('allow_public_registration', 'TRUE', 'Allow public users to register', TRUE, 1),
('maintenance_mode', 'FALSE', 'System maintenance mode', FALSE, 1);

-- Usage analytics
CREATE TABLE usage_analytics (
    id INT AUTO_INCREMENT PRIMARY KEY,
    date_recorded DATE NOT NULL,
    metric_name VARCHAR(100) NOT NULL,
    metric_value DECIMAL(15,2) NOT NULL,
    metric_type ENUM('count', 'duration', 'percentage', 'size') DEFAULT 'count',
    category VARCHAR(50),
    additional_data JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_date_metric (date_recorded, metric_name),
    INDEX idx_category (category)
);

-- Book reservations for when books are not available
CREATE TABLE book_reservations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    book_id INT NOT NULL,
    reserved_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status ENUM('active', 'fulfilled', 'cancelled', 'expired') DEFAULT 'active',
    notified BOOLEAN DEFAULT FALSE,
    expires_at TIMESTAMP NOT NULL,
    fulfilled_at TIMESTAMP NULL,
    notes TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (book_id) REFERENCES books(id),
    INDEX idx_user_status (user_id, status),
    INDEX idx_book_status (book_id, status),
    INDEX idx_expires_at (expires_at)
);

-- Reviews and ratings
CREATE TABLE book_reviews (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    book_id INT NOT NULL,
    rating INT CHECK (rating >= 1 AND rating <= 5),
    review_text TEXT,
    is_approved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (book_id) REFERENCES books(id),
    UNIQUE KEY unique_user_book_review (user_id, book_id),
    INDEX idx_book_approved (book_id, is_approved),
    INDEX idx_rating (rating)
);

-- Digital literacy progress tracking
CREATE TABLE literacy_progress (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    skill_category VARCHAR(100) NOT NULL,
    skill_name VARCHAR(200) NOT NULL,
    progress_percentage DECIMAL(5,2) DEFAULT 0.00,
    completed BOOLEAN DEFAULT FALSE,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resources_used JSON, -- Array of resource IDs used for learning
    FOREIGN KEY (user_id) REFERENCES users(id),
    INDEX idx_user_skill (user_id, skill_category),
    INDEX idx_completed (completed)
);

-- Create indexes for better performance in low-resource environments
CREATE INDEX idx_books_search_optimized ON books(is_active, is_digital, category_id, title(100));
CREATE INDEX idx_transactions_active ON borrowing_transactions(status, due_date) WHERE status IN ('borrowed', 'overdue');
CREATE INDEX idx_users_active_role ON users(is_active, role_id, district);

-- Create views for common queries to improve performance
CREATE VIEW active_borrowings AS
SELECT 
    bt.id,
    bt.user_id,
    u.username,
    u.first_name,
    u.last_name,
    bt.book_id,
    b.title,
    b.author,
    bt.borrowed_date,
    bt.due_date,
    bt.status,
    DATEDIFF(bt.due_date, CURDATE()) as days_until_due
FROM borrowing_transactions bt
JOIN users u ON bt.user_id = u.id
JOIN books b ON bt.book_id = b.id
WHERE bt.status IN ('borrowed', 'overdue');

CREATE VIEW popular_books AS
SELECT 
    b.id,
    b.title,
    b.author,
    b.category_id,
    c.name as category_name,
    b.download_count,
    b.view_count,
    (b.download_count + b.view_count) as total_activity,
    COUNT(bt.id) as borrow_count,
    AVG(br.rating) as average_rating
FROM books b
LEFT JOIN categories c ON b.category_id = c.id
LEFT JOIN borrowing_transactions bt ON b.id = bt.book_id
LEFT JOIN book_reviews br ON b.id = br.book_id AND br.is_approved = TRUE
WHERE b.is_active = TRUE
GROUP BY b.id
ORDER BY total_activity DESC, borrow_count DESC;

-- Stored procedures for common operations
DELIMITER //

CREATE PROCEDURE GetUserBorrowingHistory(IN p_user_id INT)
BEGIN
    SELECT 
        bt.id,
        b.title,
        b.author,
        bt.borrowed_date,
        bt.due_date,
        bt.returned_date,
        bt.status,
        bt.fine_amount
    FROM borrowing_transactions bt
    JOIN books b ON bt.book_id = b.id
    WHERE bt.user_id = p_user_id
    ORDER BY bt.borrowed_date DESC;
END //

CREATE PROCEDURE CheckOverdueBooks()
BEGIN
    UPDATE borrowing_transactions 
    SET status = 'overdue'
    WHERE status = 'borrowed' 
    AND due_date < CURDATE();
    
    SELECT 
        bt.id,
        u.username,
        u.email,
        b.title,
        bt.due_date,
        DATEDIFF(CURDATE(), bt.due_date) as days_overdue
    FROM borrowing_transactions bt
    JOIN users u ON bt.user_id = u.id
    JOIN books b ON bt.book_id = b.id
    WHERE bt.status = 'overdue';
END //

 

DELIMITER ;