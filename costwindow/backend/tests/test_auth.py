from app.dependencies import generate_api_key, verify_api_key


def test_api_key_starts_with_prefix():
    key, _ = generate_api_key()
    assert key.startswith("cw_live_")


def test_api_key_long_enough():
    key, _ = generate_api_key()
    assert len(key) >= 40


def test_api_key_hash_is_sha256():
    _, key_hash = generate_api_key()
    assert len(key_hash) == 64  # SHA-256 hex digest = 64 chars


def test_two_keys_are_unique():
    key1, _ = generate_api_key()
    key2, _ = generate_api_key()
    assert key1 != key2


def test_verify_correct_key():
    key, key_hash = generate_api_key()
    assert verify_api_key(key, key_hash) is True


def test_verify_wrong_key():
    _, key_hash = generate_api_key()
    assert verify_api_key("cw_live_wrongkey", key_hash) is False


def test_verify_empty_key():
    _, key_hash = generate_api_key()
    assert verify_api_key("", key_hash) is False
