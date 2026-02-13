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


# Known multi-part TLDs (suffixes). For these, the "brand" is the label before the suffix.
# E.g. bbc.co.uk -> bbc, something.com.au -> something (not "co" or "com").
MULTIPART_TLDS = frozenset({
    "co.uk", "org.uk", "me.uk", "ltd.uk", "plc.uk", "net.uk", "ac.uk", "gov.uk",
    "com.au", "org.au", "net.au", "edu.au", "gov.au", "asn.au", "id.au", "co.au",
    "co.nz", "net.nz", "org.nz", "ac.nz", "govt.nz",
    "com.br", "co.za", "co.jp", "ne.jp", "or.jp", "ac.jp",
    "com.mx", "org.mx", "gob.mx", "edu.mx",
    "com.ar", "org.ar", "gov.ar", "co.in", "org.in", "ac.in", "gov.in",
    "co.id", "or.id", "ac.id", "go.id", "web.id",
    "com.sg", "org.sg", "gov.sg", "edu.sg",
    "com.ph", "org.ph", "gov.ph", "edu.ph",
})


def source_from_url(url: str) -> str:
    """
    Derive a human-readable source name from a URL when we don't have a better label.
    Examples:
      - https://www.einpresswire.com/...        -> "Einpresswire"
      - https://news.everchem.com/...          -> "Everchem"
      - https://www.bbc.co.uk/...              -> "Bbc" (brand, not "Co")
      - https://example.com.au/...            -> "Example" (brand, not "Com")
    We do NOT perform any network I/O here; this is purely string parsing.
    """
    if not url or not isinstance(url, str):
        return ""
    try:
        p = urlparse(url)
        host = (p.netloc or "").lower()
        if not host:
            return ""
        # Strip port if present
        if ":" in host:
            host = host.split(":", 1)[0]
        # Drop common leading www.
        if host.startswith("www."):
            host = host[4:]
        parts = host.split(".")
        base = ""
        if len(parts) >= 3:
            two_part_suffix = parts[-2] + "." + parts[-1]
            if two_part_suffix in MULTIPART_TLDS:
                base = parts[-3]
            else:
                base = parts[-2]
        elif len(parts) >= 2:
            base = parts[-2]
        else:
            base = parts[0] if parts else ""
        base = base.replace("-", " ").strip()
        if not base:
            return ""
        # Title-case the base; this gives reasonable defaults like "Einpresswire", "Everchem", "Bbc"
        return base.title()
    except Exception:
        return ""
