import re
import json
import os
import sys

def extract_questions(html_path):
    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    start = content.find('const questionDatabase = [')
    if start == -1:
        print("ERROR: Could not find questionDatabase")
        sys.exit(1)
    
    # Find the end of the array
    end_marker = content.find('];', start + 50)
    if end_marker == -1:
        print("ERROR: Could not find end of questionDatabase")
        sys.exit(1)
    
    array_content = content[start:end_marker+2]
    
    # Extract questions with a simpler pattern
    question_pattern = r'\{\s*domain:\s*"([^"]+)",\s*question:\s*"((?:[^"\\]|\\.)*)"'
    matches = re.finditer(question_pattern, array_content)
    
    questions = []
    for match in matches:
        domain = match.group(1)
        question_text = match.group(2).replace('\\"', '"').replace('\\\\', '\\')
        
        # Find the full question object for this question
        obj_start = match.start()
        obj_end = array_content.find('},', obj_start)
        if obj_end == -1:
            obj_end = array_content.find('}', obj_start)
        obj_content = array_content[obj_start:obj_end+1]
        
        # Extract code if present
        code_match = re.search(r'code:\s*"((?:[^"\\]|\\.)*)"', obj_content)
        code = code_match.group(1).replace('\\"', '"').replace('\\\\', '\\') if code_match else None
        
        # Extract options
        options_match = re.search(r'options:\s*\[([^\]]+)\]', obj_content)
        options = []
        if options_match:
            options_str = options_match.group(1)
            options = re.findall(r'"((?:[^"\\]|\\.)*)"', options_str)
            options = [opt.replace('\\"', '"').replace('\\\\', '\\') for opt in options]
        
        # Extract answer
        answer_match = re.search(r'answer:\s*"((?:[^"\\]|\\.)*)"', obj_content)
        answer = answer_match.group(1).replace('\\"', '"').replace('\\\\', '\\') if answer_match else ""
        
        # Extract explanation
        explanation_match = re.search(r'explanation:\s*"((?:[^"\\]|\\.)*)"', obj_content)
        explanation = explanation_match.group(1).replace('\\"', '"').replace('\\\\', '\\') if explanation_match else ""
        
        questions.append({
            "domain": domain,
            "question_text": question_text,
            "code": code,
            "options": json.dumps(options),
            "correct_answer": answer,
            "explanation": explanation
        })
    
    print(f"Extracted {len(questions)} questions from {html_path}")
    return questions

def insert_questions(db_path, questions):
    import asyncio
    import aiosqlite
    
    async def _insert():
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        async with aiosqlite.connect(db_path) as db:
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
            print(f"Inserted {count[0]} questions into database at {db_path}")
    
    asyncio.run(_insert())

if __name__ == "__main__":
    html_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "kcsa_random.html")
    db_path = os.environ.get("DB_PATH", "/tmp/test_exams.db")
    
    questions = extract_questions(html_path)
    insert_questions(db_path, questions)
