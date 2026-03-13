"""
Deploy version helper so the running app can show which commit is actually deployed.

Primary source:
    - git rev-parse --short HEAD (real commit of the checked-out code in the container)
Fallbacks (when git metadata is unavailable, e.g. some packaging scenarios):
    - DEPLOY_VERSION.txt (short SHA written at build time, if present)
    - "local" (no deploy information available)

This ensures the on-screen "Deploy: ..." reflects the real running code by default,
instead of relying solely on a manually maintained text file.
"""

from pathlib import Path
import subprocess


def _get_git_short_sha(root: Path) -> str | None:
    """Return git rev-parse --short HEAD from the given repo root, or None if it fails."""
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        sha = (result.stdout or "").strip()
        return sha or None
    except Exception:
        return None


def get_deploy_version() -> str:
    """
    Return the short commit SHA for the running code when possible.

    Order of precedence:
    1. git rev-parse --short HEAD (actual checked-out commit in the container)
    2. DEPLOY_VERSION.txt (if present)
    3. "local" (no deploy info found)
    """
    try:
        # Repo root is parent of core/
        root = Path(__file__).resolve().parent.parent

        # 1) Truth source: git HEAD in this container
        sha = _get_git_short_sha(root)
        if sha:
            return sha

        # 2) Fallback: DEPLOY_VERSION.txt if present
        path = root / "DEPLOY_VERSION.txt"
        if path.exists():
            txt = path.read_text(encoding="utf-8").strip()
            if txt:
                return txt
    except Exception:
        pass

    # 3) Last resort
    return "local"
