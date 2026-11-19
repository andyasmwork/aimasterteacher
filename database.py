import json
import os

DB_FILE = "students_db.json"

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def get_student(user_id):
    db = load_db()
    return db.get(str(user_id), None)

def save_student_field(user_id, field, value):
    db = load_db()
    uid = str(user_id)
    if uid not in db:
        db[uid] = {
            "name": None,
            "phone": None,
            "email": None,
            "email_verified": False,
            "verification_code": None,
            "progress": [],
            "current_step": "registration"
        }
    db[uid][field] = value
    save_db(db)

def add_progress_record(user_id, lesson_name, score, comment):
    db = load_db()
    uid = str(user_id)
    if uid in db:
        db[uid]["progress"].append({
            "lesson": lesson_name,
            "score": score,
            "comment": comment
        })
        save_db(db)
