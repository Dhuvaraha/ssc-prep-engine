from app.core.security import hash_password, verify_password


def test_password_hash_round_trip():
    password = "StrongPassword123!"
    password_hash = hash_password(password)

    assert password_hash != password
    assert verify_password(password, password_hash) is True
    assert verify_password("wrong-password", password_hash) is False
