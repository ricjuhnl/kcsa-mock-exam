import aiosqlite
import asyncio
import os

DATABASE_PATH = "/app/data/exams.db"

BLUEPRINT = [
    {"domain": "Overview of Cloud Native Security (14%)", "count": 8},
    {"domain": "Kubernetes Cluster Component Security (22%)", "count": 13},
    {"domain": "Kubernetes Security Fundamentals (22%)", "count": 13},
    {"domain": "Kubernetes Threat Model (16%)", "count": 10},
    {"domain": "Platform Security (16%)", "count": 10},
    {"domain": "Compliance and Security Frameworks (10%)", "count": 6}
]

async def init_db():
    """Initialize database with tables"""
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain TEXT NOT NULL,
                question_text TEXT NOT NULL,
                code TEXT,
                options TEXT NOT NULL,
                correct_answer TEXT NOT NULL,
                explanation TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        await db.execute('''
            CREATE TABLE IF NOT EXISTS exam_sessions (
                id TEXT PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                total_questions INTEGER,
                correct_answers INTEGER,
                score REAL,
                passed BOOLEAN
            )
        ''')
        
        await db.execute('''
            CREATE TABLE IF NOT EXISTS user_responses (
                session_id TEXT,
                question_id INTEGER,
                selected_answer TEXT,
                is_correct BOOLEAN,
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (session_id, question_id),
                FOREIGN KEY (session_id) REFERENCES exam_sessions(id) ON DELETE CASCADE
            )
        ''')
        
        await db.execute('''
            CREATE INDEX IF NOT EXISTS idx_sessions_created ON exam_sessions(created_at)
        ''')
        
        await db.commit()

async def cleanup_old_sessions():
    """Delete sessions older than 7 days"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute('''
            DELETE FROM exam_sessions WHERE created_at < datetime('now', '-7 days')
        ''')
        await db.execute('''
            DELETE FROM user_responses WHERE session_id NOT IN (SELECT id FROM exam_sessions)
        ''')
        await db.commit()

def get_db_path():
    return DATABASE_PATH
