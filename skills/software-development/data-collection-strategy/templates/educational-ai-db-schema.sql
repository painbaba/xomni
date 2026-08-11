-- Educational AI Knowledge Base Schema
-- Designed for: AI products trained on past papers + marking schemes
-- Subclass: ICSE / CBSE / state-board Class 10-12
-- Reuse: copy this file, change subject names, add columns as needed

-- Subjects (the anchor table)
CREATE TABLE IF NOT EXISTS subjects (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,    -- 'Mathematics', 'Physics', 'Chemistry'
    code TEXT,                     -- 'ICSE-10-MATH', etc.
    board TEXT,                    -- 'ICSE', 'CBSE', 'STATE'
    class_level INTEGER,           -- 10, 11, 12
    total_marks INTEGER,
    time_minutes INTEGER
);

-- Syllabus with topic-level weightage
CREATE TABLE IF NOT EXISTS syllabus (
    id INTEGER PRIMARY KEY,
    subject_id INTEGER REFERENCES subjects(id),
    chapter_no INTEGER,
    chapter_name TEXT,
    topic_no INTEGER,
    topic_name TEXT,
    weightage_pct REAL,            -- expected marks % from this topic
    notes TEXT
);

-- Source artifacts (the papers themselves)
CREATE TABLE IF NOT EXISTS papers (
    id INTEGER PRIMARY KEY,
    subject_id INTEGER REFERENCES subjects(id),
    year INTEGER,
    paper_type TEXT,               -- 'specimen', 'board', 'prelim', 'model', 'mock'
    source_url TEXT,
    pdf_path TEXT,
    total_marks INTEGER,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Questions (extracted Q&A units, linked to chapter)
CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY,
    paper_id INTEGER REFERENCES papers(id),
    q_no TEXT,                     -- 'Q1(a)(i)' or 'II.3.b'
    chapter_id INTEGER REFERENCES syllabus(id),
    marks INTEGER,
    question_text TEXT,
    question_type TEXT,            -- 'mcq', 'short', 'structured', 'numerical', 'essay', 'practical'
    has_or_diagram BOOLEAN,
    section TEXT                   -- 'A', 'B', 'C' or section name
);

-- Marking schemes — THIS IS THE MOAT
-- Structured breakdown of how an examiner awards marks.
-- Generic LLMs grade generically because they lack this structure.
CREATE TABLE IF NOT EXISTS marking_schemes (
    id INTEGER PRIMARY KEY,
    question_id INTEGER REFERENCES questions(id),
    paper_id INTEGER REFERENCES papers(id),
    points TEXT,                   -- JSON: [{"concept": "...", "marks": 1}, ...]
    keywords TEXT,                 -- JSON array of expected terms
    partial_credit_rules TEXT,     -- when to give 1/2 mark, etc.
    examiner_notes TEXT,           -- "accept any valid equivalent", "do not penalise spelling"
    expected_answer_length_words INTEGER
);

-- Sample answers (real student or model answers, scored)
CREATE TABLE IF NOT EXISTS sample_answers (
    id INTEGER PRIMARY KEY,
    question_id INTEGER REFERENCES questions(id),
    answer_text TEXT,
    score_pct INTEGER,             -- how many marks this answer earned in original (out of 100)
    source TEXT,                   -- which guidebook / topper answer
    year INTEGER
);

-- Indexes for fast retrieval during AI inference
CREATE INDEX IF NOT EXISTS idx_questions_paper ON questions(paper_id);
CREATE INDEX IF NOT EXISTS idx_questions_chapter ON questions(chapter_id);
CREATE INDEX IF NOT EXISTS idx_questions_type ON questions(question_type);
CREATE INDEX IF NOT EXISTS idx_syllabus_subject ON syllabus(subject_id);
CREATE INDEX IF NOT EXISTS idx_syllabus_chapter ON syllabus(chapter_no);
CREATE INDEX IF NOT EXISTS idx_marking_question ON marking_schemes(question_id);
CREATE INDEX IF NOT EXISTS idx_marking_paper ON marking_schemes(paper_id);
CREATE INDEX IF NOT EXISTS idx_papers_subject_year ON papers(subject_id, year);

-- Example: how to query the AI KB at inference time
-- "Give me a 5-mark Physics question on chapter Force (Newton's Laws) at board exam difficulty"
-- SELECT q.question_text, ms.points, ms.keywords, ms.partial_credit_rules
-- FROM questions q
-- JOIN marking_schemes ms ON ms.question_id = q.id
-- JOIN syllabus s ON q.chapter_id = s.id
-- JOIN subjects sub ON q.paper_id IN (SELECT id FROM papers WHERE subject_id = sub.id)
-- WHERE sub.name = 'Physics' AND s.chapter_name LIKE '%Force%'
--   AND q.marks = 5 AND q.question_type = 'structured'
--   AND q.paper_id IN (SELECT id FROM papers WHERE paper_type = 'board' AND year >= 2020)
-- ORDER BY RANDOM() LIMIT 1;

-- The marking_schemes.points JSON is the critical bit — feed it as system context to the LLM
-- so it grades like an examiner (point-by-point, partial credit) instead of generic.
