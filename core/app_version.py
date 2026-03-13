"""
Deploy version read from repo so we can see which commit is running (e.g. on Streamlit Cloud).
DEPLOY_VERSION.txt in repo root holds the short git SHA; Admin and Generator show it in the sidebar.
When you push, update DEPLOY_VERSION.txt to the new short SHA (git rev-parse --short HEAD) so the app displays the correct deploy.
"""

from pathlib import Path


def get_deploy_version() -> str:
    """Return short commit SHA or 'local' if file missing. Used in sidebar so we know what code is running."""
    try:
        # Repo root is parent of core/
        root = Path(__file__).resolve().parent.parent
        path = root / "DEPLOY_VERSION.txt"
        if path.exists():
            return path.read_text(encoding="utf-8").strip() or "—"
    except Exception:
        pass
    return "local"
