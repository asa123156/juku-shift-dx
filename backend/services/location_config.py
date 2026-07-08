"""拠点ごとの時間割テンプレート・出力フォルダ設定。"""

from __future__ import annotations

import json
import re
from pathlib import Path

from fastapi import HTTPException

from config import DEFAULT_LOCATION_SLUG, LOCATIONS_DIR, OUTPUT_DIR

_SAFE_SEGMENT = re.compile(r"[^\w\-]+", re.UNICODE)


def _location_dir(slug: str) -> Path:
    path = LOCATIONS_DIR / slug
    if not path.is_dir():
        raise HTTPException(status_code=404, detail=f"拠点「{slug}」が見つかりません")
    return path


def _read_meta(path: Path) -> dict:
    meta_path = path / "location.json"
    if not meta_path.is_file():
        raise HTTPException(status_code=500, detail=f"{path.name} に location.json がありません")
    with meta_path.open(encoding="utf-8") as f:
        meta = json.load(f)
    if not isinstance(meta, dict):
        raise HTTPException(status_code=500, detail=f"{path.name}/location.json が不正です")
    return meta


def list_locations() -> list[dict]:
    if not LOCATIONS_DIR.is_dir():
        return []
    out: list[dict] = []
    for child in sorted(LOCATIONS_DIR.iterdir()):
        if not child.is_dir() or child.name.startswith("."):
            continue
        meta = _read_meta(child)
        slug = str(meta.get("slug") or child.name)
        out.append(
            {
                "slug": slug,
                "name": str(meta.get("name") or slug),
                "description": str(meta.get("description") or ""),
                "default": bool(meta.get("default")),
            }
        )
    return out


def get_default_location_slug() -> str:
    for loc in list_locations():
        if loc.get("default"):
            return loc["slug"]
    if list_locations():
        return list_locations()[0]["slug"]
    return DEFAULT_LOCATION_SLUG


def resolve_location_slug(slug: str | None) -> str:
    if slug is None or not str(slug).strip():
        return get_default_location_slug()
    normalized = str(slug).strip()
    known = {loc["slug"] for loc in list_locations()}
    if normalized not in known:
        raise HTTPException(status_code=404, detail=f"拠点「{normalized}」が見つかりません")
    return normalized


def get_location(slug: str | None = None) -> dict:
    resolved = resolve_location_slug(slug)
    meta = _read_meta(_location_dir(resolved))
    return {
        "slug": resolved,
        "name": str(meta.get("name") or resolved),
        "description": str(meta.get("description") or ""),
        "default": bool(meta.get("default")),
        "folder": str(_location_dir(resolved)),
    }


def load_grid_map(location_slug: str | None = None) -> dict:
    slug = resolve_location_slug(location_slug)
    map_path = _location_dir(slug) / "schedule_map.json"
    if not map_path.is_file():
        raise HTTPException(status_code=500, detail=f"拠点「{slug}」に schedule_map.json がありません")
    with map_path.open(encoding="utf-8") as f:
        cfg = json.load(f)
    if not isinstance(cfg, dict):
        raise HTTPException(status_code=500, detail=f"拠点「{slug}」の schedule_map.json が不正です")
    return cfg


def template_path(location_slug: str | None = None) -> Path:
    slug = resolve_location_slug(location_slug)
    cfg = load_grid_map(slug)
    filename = str(cfg.get("template_file") or "schedule_template.xlsx")
    path = _location_dir(slug) / filename
    if not path.is_file():
        raise HTTPException(status_code=500, detail=f"拠点「{slug}」のテンプレート {filename} が見つかりません")
    return path


def _safe_segment(text: str) -> str:
    cleaned = _SAFE_SEGMENT.sub("_", text.strip())
    return cleaned.strip("_") or "period"


def output_dir_for_period(
    period_id: int,
    period_name: str,
    location_slug: str | None = None,
) -> Path:
    slug = resolve_location_slug(location_slug)
    folder = OUTPUT_DIR / slug / f"{period_id}_{_safe_segment(period_name)}"
    folder.mkdir(parents=True, exist_ok=True)
    return folder
