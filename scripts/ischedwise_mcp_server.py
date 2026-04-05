"""Local MCP server for iSchedWise V4.

Run with:
    py scripts/ischedwise_mcp_server.py

Then register in VS Code / Amazon Q as stdio:
    Command: py
    Arguments: scripts/ischedwise_mcp_server.py
"""
from __future__ import annotations

from datetime import datetime

from mcp.server.fastmcp import FastMCP

from app import create_app
from app.models import Department, Faculty, Room, Schedule, Subject, User

mcp = FastMCP("ischedwise-local")

# Reuse the Flask app so DB/session config stays identical to the project.
flask_app = create_app()


@mcp.tool()
def health_check() -> dict:
    """Return basic server and project status."""
    return {
        "ok": True,
        "server": "ischedwise-local",
        "timestamp_utc": datetime.utcnow().isoformat(timespec="seconds") + "Z",
    }


@mcp.tool()
def list_routes(limit: int = 200) -> list[str]:
    """List registered Flask routes for quick API/UI discovery."""
    if limit < 1:
        limit = 1
    if limit > 1000:
        limit = 1000

    with flask_app.app_context():
        routes = sorted(
            f"{rule.endpoint} -> {rule.rule}" for rule in flask_app.url_map.iter_rules()
        )
    return routes[:limit]


@mcp.tool()
def get_core_counts() -> dict:
    """Return counts for core scheduling entities."""
    with flask_app.app_context():
        return {
            "users": User.query.count(),
            "departments": Department.query.count(),
            "faculty": Faculty.query.count(),
            "rooms": Room.query.count(),
            "subjects": Subject.query.count(),
            "class_schedules": Schedule.query.count(),
        }


@mcp.tool()
def search_faculty_by_name(keyword: str, limit: int = 20) -> list[dict]:
    """Find faculty members by name fragment."""
    keyword = (keyword or "").strip()
    if not keyword:
        return []

    if limit < 1:
        limit = 1
    if limit > 100:
        limit = 100

    with flask_app.app_context():
        rows = (
            Faculty.query.filter(Faculty.name.ilike(f"%{keyword}%"))
            .order_by(Faculty.name.asc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": row.id,
                "name": row.name,
                "department_id": row.department_id,
                "is_active": bool(getattr(row, "is_active", True)),
                "is_archived": bool(getattr(row, "is_archived", False)),
            }
            for row in rows
        ]


if __name__ == "__main__":
    mcp.run(transport="stdio")
