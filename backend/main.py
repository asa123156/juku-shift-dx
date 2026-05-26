from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# フロントエンド（React）と通信できるようにするための「おまじない」
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 開発中はどこからでもアクセスOKにする
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# シフトデータを返すAPIのルート
@app.get("/api/lessons")
def get_lessons():
    return [
        {
            "date": "2026-05-18",
            "time_slot": 1,
            "teacher_name": "前原先生",
            "students": [
                { "student_name": "近大太郎", "subject_name": "数学I" },
                { "student_name": "近大次郎", "subject_name": "英語" }
            ]
        },
        {
            "date": "2026-05-18",
            "time_slot": 1,
            "teacher_name": "浅井先生",
            "students": [
                { "student_name": "山田花子", "subject_name": "国語" }
            ]
        }
    ]