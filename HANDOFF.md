# Claude 引き継ぎメモ

最終更新: 2026-07-10  
このフォルダをそのまま渡して作業を続ける前提のメモです。

## リポジトリ

- **GitHub:** https://github.com/asa123156/juku-shift-dx.git
- **ブランチ:** `main`（`origin/main` と同期済み）
- **最新コミット:** `2a87316` — feat: add multi-location scheduling, fiscal year calendar, and workflow UI

### 直近のコミット履歴（新しい順）

| コミット | 内容 |
|----------|------|
| `2a87316` | 拠点別設定・年度カレンダー・ワークフロー UI・E2E テスト |
| `50bff55` | 初回提案送付と確定送付の分離 |
| `2105885` | 講習フローと管理画面の整備 |
| `24108f3` | アカウント資格情報の自動生成・表示 |

## 最重要: 作業ルール

**ユーザーの明示的な許可なく、講習・生徒・講師を追加しない。**

- 例外: `backend/tests/` 内のテスト作成・修正のみ
- 触らない例: `backend/data/users.json` への追加、デモデータ生成、`create_period` による講習作成、Excel インポートによるマスタ追加
- マスタ追加が必要な作業は、実装前に必ずユーザーへ確認する

Cursor 用ルールファイル（未コミット）:

```
.cursor/rules/no-master-data-without-permission.mdc
```

Claude 側でも同じ方針を守ること。

## 未コミット・未追跡ファイル

Git に入っていないもの:

| パス | 内容 |
|------|------|
| `.cursor/rules/no-master-data-without-permission.mdc` | 上記ルール（コミット推奨） |
| `ppt169_juku_shift_dx_20260701_030512.pptx` | プレゼン資料（ローカルのみ） |
| `コピー～ 202600_6月度時間割【白庭台】 .xlsx` | 参照用 Excel（ローカルのみ） |

## 起動方法

### バックエンド

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

- API: http://127.0.0.1:8000/docs
- DB: `backend/juku_shift.db`（起動時に自動作成・シード）

### フロントエンド

```bash
cd frontend
npm install
npm run dev
```

### テスト

```bash
cd backend
python -m pytest tests/ -q
```

**2026-07-10 時点: 50 tests passed**

## デモアカウント

| メール | パスワード | 役割 | 画面 |
|--------|------------|------|------|
| `admin@example.com` | `demo` | 教室長 | `/admin` |
| `teacher@example.com` | `demo` | 講師 | `/teacher` |
| `student@example.com` | `demo` | 生徒 | `/student-schedule` |

認証はモック（JWT 未実装、API 認可ガードなし）。

## プロジェクト概要

個別指導塾向けのコマ割り・シフト管理 Web アプリ。

- **フロント:** React + Vite + Tailwind（`frontend/`）
- **バック:** FastAPI + SQLAlchemy + SQLite（`backend/`）
- **仕様:** `docs/api.md`

### 主要フロー（講習）

1. 教室長が講習期間を作成 → `COLLECTING`
2. 時間割取込で生徒の `◎`（通常枠）を設定
3. 生徒が空き / `×` を提出
4. 教室長が割当 → `publish-request`（提案）→ `publish-schedule`（確定）
5. `FINALIZED` で Excel / Google 書き出し

### データストア

| 種類 | 保存先 |
|------|--------|
| Period, 割当, 提出, ダッシュボード等 | SQLite (`juku_shift.db`) |
| ログインアカウント | `backend/data/users.json` |
| 拠点設定 | `backend/locations/{slug}/` |
| Excel 出力 | `backend/output/`（gitignore、`.gitkeep` のみコミット済み） |

### 拠点（ロケーション）

デフォルト拠点: **白庭台** (`hakutei`)

```
backend/locations/hakutei/
  location.json
  schedule_map.json
  schedule_template.xlsx
```

`backend/config.py` の `DEFAULT_LOCATION_SLUG = "hakutei"`

### 直近で追加された主要機能

- **年度・カレンダー:** `academic_calendar.py`, `fiscal_year_store.py`, `routers/calendar.py`
- **講習/通常の文脈解決:** `schedule_context.py`, `schedule_canonical.py`
- **授業スケジュール正本:** `class_schedule_store.py`
- **スロット定員:** `slot_capacity_store.py`
- **管理ダッシュボード:** `admin_dashboard.py`, `AdminDashboard.jsx`
- **ワークフロー UI:** `WorkflowGuide.jsx`, `UserPhaseStepper.jsx`, `ScheduleGrid.jsx`
- **提案書エクスポート:** `proposal_export.py`
- **E2E テスト:** `test_cram_workflow_e2e.py`

### フロント主要ルート

| パス | 画面 |
|------|------|
| `/admin` | 管理ダッシュボード |
| `/admin/manage` | 期間・生徒・講師管理 |
| `/admin/student-plans` | 生徒希望教科 |
| `/admin/assignments` | 割当（生徒選択） |
| `/admin/assignments/:studentId` | 割当ボード |
| `/admin/schedule-grid` | 時間割グリッド |
| `/import` | データインポート |
| `/teacher` | 講師シフト入力 |
| `/student-schedule` | 生徒スケジュール |

## 便利スクリプト

```bash
cd backend

# スケジュール中身だけ削除（マスタは残す）
python -m scripts.clear_schedules

# 講習・生徒・講師を全削除（教室長ログインのみ残す）
python -m scripts.clear_masters
```

**注意:** `clear_masters` はマスタを消す。ユーザーの許可なく実行しない。

## 既知の注意点

1. **README.md のブランチ記載が古い** — `feat/api-shifts` と書いてあるが、現在は `main` で開発中
2. **認証・認可は未本番化** — デモ用モックログインのみ
3. **Google Sheets 連携** — 環境変数 `GOOGLE_SERVICE_ACCOUNT_FILE` または `GOOGLE_SERVICE_ACCOUNT_JSON` が必要
4. **DB と JSON の混在** — 起動時シードで JSON → SQLite へ移行。直接 JSON を編集しても SQLite 側と不整合になる場合あり
5. **コミット方針** — ユーザーが明示的に依頼したときだけ git commit / push する

## 作業再開時のおすすめ手順

1. 上記ルール（マスタ追加禁止）を確認
2. `backend` で `pytest` を実行して環境が通るか確認
3. バックエンド・フロントエンドを起動
4. `admin@example.com` / `demo` で管理画面を確認
5. 次のタスクはユーザーに確認してから着手

## 参考ドキュメント

- API 一覧: `docs/api.md`
- DFD 図: `DFD.png`（リポジトリにコミット済み）
- バックエンド詳細: `backend/README.md`
