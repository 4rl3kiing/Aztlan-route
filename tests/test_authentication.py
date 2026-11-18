import pytest

from aztlan_route.authentication import detect_authentication_challenge, detect_authentication_state


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({"url": "https://example.com/captcha", "title": "Sign in"}, "captcha_required"),
        ({"url": "https://example.com/login", "title": "Complete reCAPTCHA"}, "captcha_required"),
        ({"url": "https://example.com/login", "title": "Sign in", "captcha_element_count": 1}, "captcha_required"),
        ({"url": "https://example.com/two-factor", "title": "Verify"}, "mfa_required"),
        ({"url": "https://example.com/login", "title": "Enter verification code"}, "mfa_required"),
        ({"url": "https://example.com/login", "title": "Sign in", "mfa_element_count": 1}, "mfa_required"),
        ({"url": "https://example.com/app", "title": "Dashboard"}, None),
    ],
)
def test_detect_authentication_challenges(kwargs, expected):
    assert detect_authentication_challenge(**kwargs) == expected


def test_captcha_takes_precedence_over_mfa():
    assert detect_authentication_challenge(
        url="https://example.com/captcha",
        title="Verify",
        mfa_element_count=1,
    ) == "captcha_required"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"url": None, "title": "Login"},
        {"url": "https://example.com", "title": None},
        {"url": "https://example.com", "title": "Login", "captcha_element_count": True},
        {"url": "https://example.com", "title": "Login", "mfa_element_count": -1},
    ],
)
def test_invalid_detector_input_is_ignored(kwargs):
    assert detect_authentication_challenge(**kwargs) is None



@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({"url": "https://example.com/login", "title": "Sign in"}, "reauthentication_required"),
        ({"url": "https://example.com/session-expired", "title": "Welcome"}, "reauthentication_required"),
        ({"url": "https://example.com/account", "title": "Account", "login_form_detected": True}, "reauthentication_required"),
        ({"url": "https://example.com/app", "title": "Dashboard"}, None),
        ({"url": "https://example.com/app", "title": "Dashboard", "login_form_detected": False}, None),
    ],
)
def test_detect_reauthentication_state(kwargs, expected):
    assert detect_authentication_state(**kwargs) == expected


def test_challenge_state_takes_precedence_over_reauthentication():
    assert detect_authentication_state(
        url="https://example.com/login",
        title="Sign in",
        captcha_element_count=1,
    ) == "captcha_required"
