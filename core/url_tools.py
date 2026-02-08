"""
URL canonicalization and validation for V2 Evidence Engine.
Rules: accept 2xx and 3xx as valid; mark 403 as restricted (do not drop).
"""

from typing import Tuple, Optional
from urllib.parse import urlparse, urlunparse
import re

try:
    import urllib.request
    import urllib.error
    _HAS_URLLIB = True
except ImportError:
    urllib = None  # type: ignore
    _HAS_URLLIB = False

# Status enum values matching DB url_validation_status
VALID_2XX = "valid_2xx"
VALID_3XX = "valid_3xx"
RESTRICTED_403 = "restricted_403"
ERROR_OTHER = "error_other"
NOT_CHECKED = "not_checked"


def canonicalize_url(url: str) -> str:
    """Normalize URL for deduplication: scheme+netloc lowercase, strip fragment, sort query (optional)."""
    if not url or not isinstance(url, str):
        return ""
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        return url
    try:
        p = urlparse(url)
        netloc = p.netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        path = p.path or "/"
        path = re.sub(r"/+", "/", path)
        if path != "/" and path.endswith("/"):
            path = path.rstrip("/")
        q = p.query
        return urlunparse((p.scheme.lower(), netloc, path, p.params, q, ""))
    except Exception:
        return url


def validate_url(url: str, timeout: int = 8) -> Tuple[str, Optional[int]]:
    """
    Validate URL via HEAD then GET fallback.
    Returns (validation_status, http_status_code).
    - valid_2xx: 2xx response
    - valid_3xx: 3xx response (redirect)
    - restricted_403: 403 Forbidden (do not drop)
    - error_other: other error or timeout
    - not_checked: skipped (e.g. no urllib)
    """
    if not url or not url.startswith(("http://", "https://")):
        return ERROR_OTHER, None
    if not _HAS_URLLIB:
        return NOT_CHECKED, None
    try:
        req = urllib.request.Request(url, method="HEAD")
        req.add_header("User-Agent", "Mozilla/5.0 (compatible; PU-Observatory/2.0)")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            code = r.getcode()
            if 200 <= code < 300:
                return VALID_2XX, code
            if 300 <= code < 400:
                return VALID_3XX, code
            if code == 403:
                return RESTRICTED_403, code
            return ERROR_OTHER, code
    except urllib.error.HTTPError as e:
        code = e.code
        if code == 403:
            return RESTRICTED_403, code
        return ERROR_OTHER, code
    except Exception:
        try:
            req = urllib.request.Request(url, method="GET")
            req.add_header("User-Agent", "Mozilla/5.0 (compatible; PU-Observatory/2.0)")
            with urllib.request.urlopen(req, timeout=timeout) as r:
                code = r.getcode()
                if 200 <= code < 300:
                    return VALID_2XX, code
                if 300 <= code < 400:
                    return VALID_3XX, code
                if code == 403:
                    return RESTRICTED_403, code
                return ERROR_OTHER, code
        except urllib.error.HTTPError as e:
            if e.code == 403:
                return RESTRICTED_403, e.code
            return ERROR_OTHER, e.code
        except Exception:
            return ERROR_OTHER, None
