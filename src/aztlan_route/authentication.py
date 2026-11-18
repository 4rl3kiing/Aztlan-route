"""Conservative, non-invasive detection of interactive authentication challenges."""
from __future__ import annotations

from urllib.parse import urlparse


def _path_segments(url: str) -> set[str] | None:
    if not isinstance(url, str):
        return None
    try:
        parsed = urlparse(url)
    except ValueError:
        return None
    return {segment.lower() for segment in parsed.path.split("/") if segment}


def detect_authentication_challenge(
    *,
    url: str,
    title: str = "",
    captcha_element_count: int = 0,
    mfa_element_count: int = 0,
) -> str | None:
    """Detect explicit challenge elements or exact challenge path segments.

    Page titles and query strings are deliberately ignored: generic words such as
    "challenge", "verification" or "otp" cause false positives on ordinary pages.
    The detector never reads page body text, credentials, cookies or storage.
    """
    if not isinstance(title, str):
        return None
    if type(captcha_element_count) is not int or captcha_element_count < 0:
        return None
    if type(mfa_element_count) is not int or mfa_element_count < 0:
        return None
    segments = _path_segments(url)
    if segments is None:
        return None

    captcha_paths = {"captcha", "recaptcha", "hcaptcha", "turnstile"}
    mfa_paths = {"two-factor", "two_factor", "2fa", "mfa", "otp", "verify-device"}
    if captcha_element_count or segments & captcha_paths:
        return "captcha_required"
    if mfa_element_count or segments & mfa_paths:
        return "mfa_required"
    return None


def detect_authentication_state(
    *,
    url: str,
    title: str = "",
    captcha_element_count: int = 0,
    mfa_element_count: int = 0,
) -> str | None:
    """Detect explicit challenge or a recognized sign-in route."""
    if not isinstance(title, str):
        return None
    challenge = detect_authentication_challenge(
        url=url,
        title=title,
        captcha_element_count=captcha_element_count,
        mfa_element_count=mfa_element_count,
    )
    if challenge:
        return challenge
    segments = _path_segments(url)
    if segments is None:
        return None
    login_paths = {
        "login", "log-in", "signin", "sign-in", "session-expired",
        "reauthenticate", "reauth",
    }
    if segments & login_paths:
        return "reauthentication_required"
    return None
