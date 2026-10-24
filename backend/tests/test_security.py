from app.core.security import create_access_token, decode_access_token, hash_password, verify_password


def test_password_hash_is_one_way_and_verifies() -> None:
    encoded = hash_password("a-long-development-password")
    assert encoded != "a-long-development-password"
    assert verify_password("a-long-development-password", encoded)
    assert not verify_password("wrong-password", encoded)


def test_access_token_round_trip() -> None:
    token = create_access_token("42")
    assert decode_access_token(token) == "42"
    assert decode_access_token("not-a-token") is None