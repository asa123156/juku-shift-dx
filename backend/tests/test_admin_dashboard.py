"""ダッシュボード summary API のテスト。"""

from services.admin_dashboard import build_admin_dashboard_summary
from services.schedule_publish_store import publish_student_schedule_request


def test_dashboard_member_lists():
    summary = build_admin_dashboard_summary(1)
    assert "students" in summary
    assert "teachers" in summary
    assert "proposal_sent" in summary["students"]
    assert "unsubmitted" in summary["students"]
    assert "schedule_published" in summary["students"]
    for key in ("proposal_sent", "unsubmitted", "schedule_published"):
        assert isinstance(summary["students"][key], list)
        assert isinstance(summary["teachers"][key], list)

    publish_student_schedule_request(1, 1)
    after = build_admin_dashboard_summary(1)
    names = [s["name"] for s in after["students"]["proposal_sent"]]
    assert "workflow_steps" in after
    assert len(after["workflow_steps"]) == 6
    assert after["workflow_steps"][0]["title"] == "講習作成・希望設定"
