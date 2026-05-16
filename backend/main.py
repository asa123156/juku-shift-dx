from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Hello Juku DX Backend!"}

# 友達に渡した「JSONの形」を返す窓口（API）の試作品
@app.get("/api/lessons")
def get_lessons():
    return [
        {
            "date": "2026-05-18",
            "time_slot": 1,
            "teacher_name": "前原先生",
            "students": [
                { "student_name": "近大太郎", "subject_name": "数学I" }
            ]
        }
    ]