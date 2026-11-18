import pytest

from aztlan_route.authentication import (
    detect_authentication_challenge,
    detect_authentication_state,
)


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({"url": "https://example.com/captcha"}, "captcha_required"),
        ({"url": "https://example.com/recaptcha/verify"}, "captcha_required"),
        ({"url": "https://example.com/login", "captcha_element_count": 1}, "captcha_required"),
        ({"url": "https://example.com/two-factor"}, "mfa_required"),
        ({"url": "https://example.com/otp/verify"}, "mfa_required"),
        ({"url": "https://example.com/login", "mfa_element_count": 1}, "mfa_required"),
        ({"url": "https://example.com/app"}, None),
    ],
)
def test_detect_authentication_challenges(kwargs, expected):
    assert detect_authentication_challenge(**kwargs) == expected


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({"url": "https://example.com/login"}, "reauthentication_required"),
        ({"url": "https://example.com/session-expired"}, "reauthentication_required"),
        ({"url": "https://example.com/account"}, None),
        ({"url": "https://example.com/app"}, None),
    ],
)
def test_detect_reauthentication_state(kwargs, expected):
    assert detect_authentication_state(**kwargs) == expected


@pytest.mark.parametrize(
    "url,title",
    [
        ("https://example.com/app?challenge=abc", "Dashboard"),
        ("https://example.com/app?verification=required", "Verification"),
        ("https://example.com/app", "Complete challenge"),
        ("https://example.com/app", "Enter OTP"),
        ("https://example.com/app", "Password manager"),
    ],
)
def test_generic_query_and_title_words_do_not_trigger_challenge(url, title):
    assert detect_authentication_challenge(url=url, title=title) is None
    assert detect_authentication_state(url=url, title=title) is None


def test_captcha_elements_take_precedence_over_mfa_elements():
    assert detect_authentication_challenge(
        url="https://example.com/app",
        captcha_element_count=1,
        mfa_element_count=1,
    ) == "captcha_required"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"url": None},
        {"url": "https://example.com", "captcha_element_count": True},
        {"url": "https://example.com", "mfa_element_count": -1},
    ],
)
def test_invalid_detector_input_is_ignored(kwargs):
    assert detect_authentication_challenge(**kwargs) is None
