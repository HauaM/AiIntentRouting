from intent_routing.security.admin_passwords import (
    hash_admin_password,
    verify_admin_password,
)


def test_admin_password_hash_verifies_without_storing_raw_password() -> None:
    password = "correct horse battery staple"

    password_hash = hash_admin_password(password)

    assert password not in password_hash
    assert verify_admin_password(password, password_hash) is True


def test_admin_password_verify_rejects_wrong_password() -> None:
    password_hash = hash_admin_password("correct-password")

    assert verify_admin_password("wrong-password", password_hash) is False
