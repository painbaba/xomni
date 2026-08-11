-- Reusable SQLite schema for an AI knowledge base backed by scraped public content.
-- Designed for: exam-prep AI, doubt-solving AI, marking-scheme grading AI, tutor AI.
-- Pattern: subjects → syllabus → papers → questions → marking_schemes → sample_answers
-- Plus a `yt_videos` reference table for public video links (not training data).

CREATE TABLE IF NOT EXISTS subjects (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,           -- 'Mathematics', 'Physics', 'Chemistry'
    code TEXT,                            -- 'ICSE-10-MATH' etc.
    total_marks INTEGER,
    time_minutes INTEGER
);

CREATE TABLE IF NOT EXISTS syllabus (
    id INTEGER PRIMARY KEY,
    subject_id INTEGER REFERENCES subjects(id),
    chapter_no INTEGER,
    chapter_name TEXT,
    topic_no INTEGER,
    topic_name TEXT,
    weightage_pct REAL,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS papers (
    id INTEGER PRIMARY KEY,
    subject_id INTEGER REFERENCES subjects(id),
    year INTEGER,
    paper_type TEXT,                      -- 'specimen', 'board', 'prelim', 'model'
    source_url TEXT,
    pdf_path TEXT,
    total_marks INTEGER,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY,
    paper_id INTEGER REFERENCES papers(id),
    q_no TEXT,                            -- 'Q1(a)(i)' etc.
    chapter_id INTEGER REFERENCES syllabus(id),
    marks INTEGER,
    question_text TEXT,
    question_type TEXT,                   -- 'mcq', 'short', 'structured', 'numerical', 'essay'
    has_or_diagram BOOLEAN,
    section TEXT
);

CREATE TABLE IF NOT EXISTS marking_schemes (
    id INTEGER PRIMARY KEY,
    question_id INTEGER REFERENCES questions(id),
    paper_id INTEGER REFERENCES papers(id),
    points TEXT,                          -- JSON: breakdown of marks per concept
    keywords TEXT,                        -- JSON array of expected terms
    partial_credit_rules TEXT,
    examiner_notes TEXT
);

CREATE TABLE IF NOT EXISTS sample_answers (
    id INTEGER PRIMARY KEY,
    question_id INTEGER REFERENCES questions(id),
    answer_text TEXT,
    score_pct INTEGER,                    -- how many marks this answer earned in original
    source TEXT,                          -- which guidebook / topper
    year INTEGER
);

-- Public video references. Link only — do not store audio, video, or transcripts.
CREATE TABLE IF NOT EXISTS yt_videos (
    id INTEGER PRIMARY KEY,
    subject TEXT,
    yt_id TEXT UNIQUE,                    -- yt-dlp id, enforces dedup
    title TEXT,
    channel TEXT,
    channel_id TEXT,
    duration_sec INTEGER,
    view_count INTEGER,
    like_count INTEGER,
    upload_date TEXT,
    description TEXT,
    url TEXT,
    search_query TEXT,
    video_type TEXT                       -- 'topper_strategy' | 'project_walkthrough' | 'specimen_paper_solution' | 'practical_guide' | 'exam_strategy' | 'working_model' | 'general'
);

-- Indexes for fast retrieval during AI inference
CREATE INDEX IF NOT EXISTS idx_questions_paper ON questions(paper_id);
CREATE INDEX IF NOT EXISTS idx_questions_chapter ON questions(chapter_id);
CREATE INDEX IF NOT EXISTS idx_syllabus_subject ON syllabus(subject_id);
CREATE INDEX IF NOT EXISTS idx_marking_question ON marking_schemes(question_id);
CREATE INDEX IF NOT EXISTS idx_yt_subject ON yt_videos(subject);
CREATE INDEX IF NOT EXISTS idx_yt_views ON yt_videos(view_count DESC);
CREATE INDEX IF NOT EXISTS idx_yt_type ON yt_videos(video_type);

-- Bootstrap insert for typical use case (3 subjects)
INSERT OR IGNORE INTO subjects (name, code) VALUES
    ('Mathematics', 'ICSE-10-MATH'),
    ('Physics',      'ICSE-10-PHY'),
    ('Chemistry',    'ICSE-10-CHEM');
