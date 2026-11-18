"""Conservative, non-invasive detection of interactive authentication challenges."""
from __future__ import annotations

from urllib.parse import urlparse


def detect_authentication_challenge(
    *,
    url: str,
    title: str,
    captcha_element_count: int = 0,
    mfa_element_count: int = 0,
) -> str | None:
    """Return a challenge state based on URL/title and visible challenge elements.

    The detector never solves challenges, reads page body text, or accesses credentials,
    cookies, local storage, or authentication tokens. A missing challenge is not proof
    that authentication succeeded; success requires explicit operator confirmation.
    """
    if not isinstance(url, str) or not isinstance(title, str):
        return None
    if type(captcha_element_count) is not int or captcha_element_count < 0:
        return None
    if type(mfa_element_count) is not int or mfa_element_count < 0:
        return None

    parsed = urlparse(url.lower())
    path_and_query = f"{parsed.path}?{parsed.query}"
    title_lower = title.lower()

    captcha_markers = ("captcha", "recaptcha", "hcaptcha", "turnstile", "challenge")
    mfa_markers = (
        "two-factor", "two_factor", "2fa", "mfa", "otp", "verify-device",
        "verification", "authenticator",
    )

    if captcha_element_count or any(
        marker in path_and_query or marker in title_lower for marker in captcha_markers
    ):
        return "captcha_required"
    if mfa_element_count or any(
        marker in path_and_query or marker in title_lower for marker in mfa_markers
    ):
        return "mfa_required"
    return None



def detect_authentication_state(
    *,
    url: str,
    title: str,
    captcha_element_count: int = 0,
    mfa_element_count: int = 0,
    login_form_detected: bool = False,
) -> str | None:
    """Detect explicit challenge or sign-in indicators without inspecting credentials."""
    if not isinstance(url, str) or not isinstance(title, str):
        return None
    challenge = detect_authentication_challenge(
        url=url,
        title=title,
        captcha_element_count=captcha_element_count,
        mfa_element_count=mfa_element_count,
    )
    if challenge:
        return challenge
    if type(login_form_detected) is not bool:
        return None
    path = urlparse(url.lower()).path.rstrip("/") or "/"
    login_paths = (
        "/login", "/log-in", "/signin", "/sign-in", "/session-expired",
        "/reauthenticate", "/reauth",
    )
    if path in login_paths or any(path.endswith(marker) for marker in login_paths):
        return "reauthentication_required"
    if login_form_detected:
        return "reauthentication_required"
    return None
