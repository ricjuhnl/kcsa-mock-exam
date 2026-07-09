import os
import sys
import json
import random
import asyncio
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Request, Depends, Header
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.database import init_db, cleanup_old_sessions, get_db_path, BLUEPRINT
from app.models import (
    QuestionCreate, QuestionUpdate, QuestionResponse,
    SessionCreate, SessionResponse, SessionSubmit, SessionResult, SessionListItem,
    generate_session_id
)
import aiosqlite

app = FastAPI(title="KCSA Exam API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "admin")

@app.on_event("startup")
async def startup_event():
    await init_db()
    await cleanup_old_sessions()
    await seed_questions_if_empty()

async def seed_questions_if_empty():
    db_path = get_db_path()
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM questions")
        count = await cursor.fetchone()
        if count[0] == 0:
            html_path = os.path.join(os.path.dirname(__file__), "kcsa_random.html")
            if os.path.exists(html_path):
                from app.seed import extract_questions
                questions = extract_questions(html_path)
                await insert_questions_async(db_path, questions)

async def insert_questions_async(db_path, questions):
    async with aiosqlite.connect(db_path) as db:
        for q in questions:
            await db.execute(
                '''INSERT OR IGNORE INTO questions 
                   (domain, question_text, code, options, correct_answer, explanation)
                   VALUES (?, ?, ?, ?, ?, ?)''',
                (q["domain"], q["question_text"], q["code"], 
                 q["options"], q["correct_answer"], q["explanation"])
            )
        await db.commit()
        cursor = await db.execute("SELECT COUNT(*) FROM questions")
        count = await cursor.fetchone()
        print(f"Seeded {count[0]} questions into database")

def verify_admin_authorization(authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "basic":
        raise HTTPException(status_code=401, detail="Invalid authorization format")
    
    import base64
    try:
        credentials = base64.b64decode(parts[1]).decode("utf-8")
        username, password = credentials.split(":", 1)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid credentials encoding")
    
    if username != ADMIN_USER or password != ADMIN_PASS:
        raise HTTPException(status_code=401, detail="Invalid credentials")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.get("/api/questions")
async def get_questions():
    db_path = get_db_path()
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        questions = []
        
        for target in BLUEPRINT:
            domain = target["domain"]
            count = target["count"]
            
            cursor = await db.execute(
                "SELECT * FROM questions WHERE domain = ? ORDER BY RANDOM() LIMIT ?",
                (domain, count)
            )
            domain_questions = await cursor.fetchall()
            
            for row in domain_questions:
                questions.append({
                    "id": row["id"],
                    "domain": row["domain"],
                    "question": row["question_text"],
                    "code": row["code"],
                    "options": json.loads(row["options"]),
                    "answer": row["correct_answer"],
                    "explanation": row["explanation"]
                })
        
        random.shuffle(questions)
        
        return {"questions": questions, "total": len(questions)}

@app.post("/api/sessions")
async def create_session():
    session_id = generate_session_id()
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute(
            "INSERT INTO exam_sessions (id, created_at) VALUES (?, ?)",
            (session_id, datetime.utcnow().isoformat())
        )
        await db.commit()
    
    return {"sessionId": session_id}

@app.post("/api/sessions/{session_id}/submit")
async def submit_session(session_id: str, submission: SessionSubmit):
    async with aiosqlite.connect(get_db_path()) as db:
        cursor = await db.execute("SELECT * FROM exam_sessions WHERE id = ?", (session_id,))
        session = await cursor.fetchone()
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        answers = submission.answers
        questions_db = {}
        
        db.row_factory = aiosqlite.Row
        for q_id in answers.keys():
            cursor = await db.execute("SELECT * FROM questions WHERE id = ?", (q_id,))
            q = await cursor.fetchone()
            if q:
                questions_db[q_id] = q
        
        correct_count = 0
        domain_stats = {}
        
        for blueprint_target in BLUEPRINT:
            domain = blueprint_target["domain"]
            domain_stats[domain] = {"correct": 0, "total": 0}
        
        # Check if questions were actually found in the database
        if not questions_db and answers:
            raise HTTPException(
                status_code=500,
                detail="No questions found in database. The question bank may not be properly seeded."
            )
        
        for q_id, selected_idx in answers.items():
            # Convert question ID to integer for consistent lookup
            try:
                q_id_int = int(q_id)
            except (ValueError, TypeError):
                continue
            
            q = questions_db.get(q_id) or questions_db.get(q_id_int)
            if q:
                options = json.loads(q["options"])
                selected_text = options[selected_idx] if selected_idx < len(options) else ""
                correct_text = q["correct_answer"]
                
                is_correct = selected_text == correct_text
                if is_correct:
                    correct_count += 1
                
                domain = q["domain"]
                if domain in domain_stats:
                    domain_stats[domain]["total"] += 1
                    if is_correct:
                        domain_stats[domain]["correct"] += 1
                
                await db.execute(
                    "INSERT OR IGNORE INTO user_responses (session_id, question_id, selected_answer, is_correct) VALUES (?, ?, ?, ?)",
                    (session_id, q_id_int, selected_text, is_correct)
                )
        
        total_questions = len(answers)
        score = round((correct_count / total_questions * 100) if total_questions > 0 else 0, 2)
        passed = score >= 75
        
        await db.execute(
            """UPDATE exam_sessions 
               SET completed_at = ?, total_questions = ?, correct_answers = ?, score = ?, passed = ?
               WHERE id = ?""",
            (datetime.utcnow().isoformat(), total_questions, correct_count, score, passed, session_id)
        )
        await db.commit()
        
        breakdown = {}
        for domain, stats in domain_stats.items():
            pct = round((stats["correct"] / stats["total"] * 100) if stats["total"] > 0 else 0, 2)
            breakdown[domain] = {
                "correct": stats["correct"],
                "total": stats["total"],
                "percentage": pct
            }
        
        return {
            "sessionId": session_id,
            "totalQuestions": total_questions,
            "correctAnswers": correct_count,
            "score": score,
            "passed": passed,
            "domainBreakdown": breakdown
        }

@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    async with aiosqlite.connect(get_db_path()) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM exam_sessions WHERE id = ?", (session_id,))
        session = await cursor.fetchone()
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        cursor = await db.execute(
            """SELECT ur.session_id, ur.question_id, ur.selected_answer, ur.is_correct, ur.submitted_at,
                      q.domain, q.question_text
               FROM user_responses ur
               LEFT JOIN questions q ON ur.question_id = q.id
               WHERE ur.session_id = ?""",
            (session_id,)
        )
        responses = await cursor.fetchall()
        
        return {
            "id": session["id"],
            "created_at": session["created_at"],
            "completed_at": session["completed_at"],
            "totalQuestions": session["total_questions"],
            "correctAnswers": session["correct_answers"],
            "score": session["score"],
            "passed": session["passed"],
            "responses": [dict(r) for r in responses]
        }

@app.get("/api/admin/questions")
async def admin_list_questions(authorization: Optional[str] = Header(None)):
    verify_admin_authorization(authorization)
    
    async with aiosqlite.connect(get_db_path()) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM questions ORDER BY domain, id")
        questions = await cursor.fetchall()
        
        return [dict(q) for q in questions]

@app.post("/api/admin/questions")
async def admin_create_question(data: QuestionCreate, authorization: Optional[str] = Header(None)):
    verify_admin_authorization(authorization)
    
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute(
            """INSERT INTO questions (domain, question_text, code, options, correct_answer, explanation)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (data.domain, data.question_text, data.code, json.dumps(data.options), 
             data.correct_answer, data.explanation)
        )
        await db.commit()
        
        return {"id": 1, "message": "Question created successfully"}

@app.put("/api/admin/questions/{question_id}")
async def admin_update_question(question_id: int, data: QuestionUpdate, authorization: Optional[str] = Header(None)):
    verify_admin_authorization(authorization)
    
    updates = {}
    if data.domain is not None:
        updates["domain"] = data.domain
    if data.question_text is not None:
        updates["question_text"] = data.question_text
    if data.code is not None:
        updates["code"] = data.code
    if data.options is not None:
        updates["options"] = json.dumps(data.options)
    if data.correct_answer is not None:
        updates["correct_answer"] = data.correct_answer
    if data.explanation is not None:
        updates["explanation"] = data.explanation
    
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
    values = list(updates.values()) + [question_id]
    
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute(f"UPDATE questions SET {set_clause} WHERE id = ?", values)
        await db.commit()
        
        return {"message": "Question updated successfully"}

@app.delete("/api/admin/questions/{question_id}")
async def admin_delete_question(question_id: int, authorization: Optional[str] = Header(None)):
    verify_admin_authorization(authorization)
    
    async with aiosqlite.connect(get_db_path()) as db:
        cursor = await db.execute("DELETE FROM questions WHERE id = ?", (question_id,))
        await db.commit()
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Question not found")
        
        return {"message": "Question deleted successfully"}

@app.get("/api/admin/sessions")
async def admin_list_sessions(authorization: Optional[str] = Header(None)):
    verify_admin_authorization(authorization)
    
    async with aiosqlite.connect(get_db_path()) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM exam_sessions ORDER BY created_at DESC LIMIT 100"
        )
        sessions = await cursor.fetchall()
        
        return [dict(s) for s in sessions]

@app.get("/api/admin/stats")
async def admin_stats(authorization: Optional[str] = Header(None)):
    verify_admin_authorization(authorization)
    
    async with aiosqlite.connect(get_db_path()) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM exam_sessions")
        total_sessions = (await cursor.fetchone())[0]
        
        cursor = await db.execute("SELECT COUNT(*) FROM questions")
        total_questions = (await cursor.fetchone())[0]
        
        cursor = await db.execute("SELECT AVG(score) FROM exam_sessions WHERE score IS NOT NULL")
        avg_score = (await cursor.fetchone())[0] or 0
        
        cursor = await db.execute("SELECT COUNT(*) FROM exam_sessions WHERE passed = 1")
        passed_count = (await cursor.fetchone())[0]
        pass_rate = round((passed_count / total_sessions * 100) if total_sessions > 0 else 0, 2)
        
        domain_stats = {}
        cursor = await db.execute(
            """SELECT q.domain, 
                      COUNT(*) as total,
                      SUM(CASE WHEN ur.is_correct = 1 THEN 1 ELSE 0 END) as correct
               FROM user_responses ur
               JOIN questions q ON ur.question_id = q.id
               GROUP BY q.domain"""
        )
        for row in await cursor.fetchall():
            domain_stats[row[0]] = {
                "total": row[1],
                "correct": row[2],
                "percentage": round((row[2] / row[1] * 100) if row[1] > 0 else 0, 2)
            }
        
        return {
            "totalSessions": total_sessions,
            "totalQuestions": total_questions,
            "averageScore": round(avg_score, 2),
            "passRate": pass_rate,
            "domainBreakdown": domain_stats
        }
