# JUKU-SHIFT DX API 一覧

ベース URL（開発）: `http://127.0.0.1:8000`  
Swagger: http://127.0.0.1:8000/docs

## 認証（モック）

### `POST /api/auth/login`

| メール | パスワード | 役割 | 遷移先 |
|--------|------------|------|--------|
| `teacher@example.com` | `demo` | 講師 (`teacher_id: 1`) | `/student` |
| `student@example.com` | `demo` | 生徒 (`student_id: 1`) | `/student-schedule` |
| `admin@example.com` | `demo` | 教室長 | `/admin` |

本番では JWT 等に差し替え予定。API ルートに認可ガードは未実装です。

## シフト・スケジュール

| メソッド | パス | 説明 |
|----------|------|------|
| GET | `/api/shifts/dates` | 利用可能な日付一覧 |
| GET | `/api/shifts/teachers?date=` | 講師一覧（id, name, color） |
| GET | `/api/shifts?date=` | 教室長ダッシュボード |
| GET | `/api/shifts/me?teacher_id=&date=` | 講師入力（◎/×/空） |
| GET | `/api/shifts/my-schedule?role=&entity_id=&period_id=` | 講師・生徒の期間スケジュール（確定後は readonly） |
| POST | `/api/shifts` | 講師が1日分提出 |
| PATCH | `/api/shifts` | 講師が1コマ更新 |
| PATCH | `/api/shifts/bulk` | 期間一括提出（講師・生徒） |
| POST | `/api/shifts/change-requests` | 送付済みスケジュールの変更申請 |
| GET | `/api/shifts/time-slots` | コマ時刻定義 |

### 生徒提出記号

| 記号 | 意味 |
|------|------|
| `通常:数学` | 通常授業として数学を希望 |
| `講習:英語` | 講習として英語を希望 |
| `×` | 不可 |
| 空 | 未指定（柔軟） |

## 教室長操作

| メソッド | パス | 説明 |
|----------|------|------|
| PATCH | `/api/admin/shifts/slot` | コマのステータスを直接変更 |
| POST | `/api/admin/shifts/confirm` | （非推奨）シフト確定は期間 FINALIZED を使用 |
| GET | `/api/admin/periods` | 募集期間一覧 |
| POST | `/api/admin/periods` | 募集期間作成（`closed_dates` で休校日指定可） |
| PATCH | `/api/admin/periods/{id}/status` | DRAFT → COLLECTING → FINALIZED |
| GET | `/api/admin/assignments/sheets?period_id=` | 期間の割当シート（生徒・講師） |
| GET | `/api/admin/assignments/grid?date=` | 1日分の割当グリッド |
| POST | `/api/admin/assignments/candidates` | 自動割当候補（NGルール適用後） |
| POST | `/api/admin/assignments/manual` | 手動割当 |
| POST | `/api/admin/assignments/cancel` | 割当解除 |
| POST | `/api/admin/auto-assign` | 1日分の自動割当 |
| POST | `/api/admin/auto-assign-period` | 期間全体の自動割当 |
| POST | `/api/admin/assignments/publish-schedule` | 生徒に確定スケジュール送付 |
| POST | `/api/admin/assignments/publish-teacher-schedule` | 講師に確定スケジュール送付 |
| POST | `/api/admin/assignments/publish-all` | 割当済み生徒・全講師に一括送付 |
| POST | `/api/admin/assignment-requests/import` | CSV から未割当リクエスト取込 |
| GET | `/api/admin/change-requests?period_id=&status=` | 変更申請一覧 |
| PATCH | `/api/admin/change-requests/{id}` | 変更申請の承認/却下 |
| GET/POST/PATCH | `/api/admin/students` 等 | 生徒・講師マスタ CRUD |
| GET/PUT | `/api/admin/periods/{id}/student-plans` | 生徒希望教科 |
| POST | `/api/admin/shifts/import-excel` | 通常授業（◎）CSV 取込 |
| GET | `/api/admin/shifts/export-excel` | 確定シフト CSV 出力 |
| POST | `/api/import/juku-grid` | 月次時間割 xlsx 取込 |
| GET | `/api/export/juku-schedule` | インポート済み Excel に割当反映 |
| GET | `/api/google/status` | Google Sheets 連携の設定状態 |
| POST | `/api/google/import` | Google スプレッドシートから時間割取込 |
| POST | `/api/google/export` | 確定時間割を Google へ書き出し |

### 期間ステータスと送付の関係

1. **COLLECTING** — 講師・生徒が提出、教室長が割当
2. **publish-schedule / publish-teacher-schedule** — 個人に確定スケジュール送付（readonly 化）
3. **FINALIZED** — 募集締切。Excel / Google 書き出し可能

### Google Sheets 連携

環境変数（いずれか）:

- `GOOGLE_SERVICE_ACCOUNT_FILE` — サービスアカウント JSON のファイルパス
- `GOOGLE_SERVICE_ACCOUNT_JSON` — 同上 JSON を文字列で直接指定

### 自動割当ルール

1. 講師コマが「不可」→ 除外
2. 生徒提出が `×` のコマ → 除外
3. 生徒提出が `通常:科目` / `講習:科目` で科目不一致 → 除外
4. 科目ごとの週コマ上限（国語1・数学2 等）
5. 空きコマなし（講師）
6. 生徒3コマ連続不可 / 講師4コマ連続不可（裏ルール）

## 授業コマ割り（モック）

| メソッド | パス | 説明 |
|----------|------|------|
| GET | `/api/lessons?date=` | `docs/lesson_mock.json`（フロント未接続） |

## データストア

主要データは SQLite（`backend/juku_shift.db`）。ログイン用 `users.json` のみ JSON。

詳細・例: [api-shifts.md](./api-shifts.md)
