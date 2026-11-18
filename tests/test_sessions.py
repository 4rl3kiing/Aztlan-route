from aztlan_route.sessions import SessionManager


def test_lists_profiles_without_reading_profile_contents(tmp_path):
    (tmp_path / "qwen" / "firefox").mkdir(parents=True)
    (tmp_path / "qwen" / "chromium").mkdir(parents=True)
    (tmp_path / "other" / "webkit").mkdir(parents=True)
    profiles = SessionManager(tmp_path).list_profiles()
    assert [(p.provider_id, p.browser) for p in profiles] == [
        ("qwen", "chromium"), ("qwen", "firefox")
    ]
