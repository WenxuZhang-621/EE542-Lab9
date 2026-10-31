import pytest
from fastapi import HTTPException
from webapp.backend.public_access import PublicAccess


def test_public_configuration_fails_closed():
    with pytest.raises(RuntimeError):
        PublicAccess(True, '')


def test_global_hourly_limit_across_users_and_window_expiry():
    now = [0.0]
    guard = PublicAccess(True, 'test-group-invitation', lambda: now[0])
    for user in range(60):
        with guard.message(user, True):
            pass
        now[0] += 2
    with pytest.raises(HTTPException) as error:
        with guard.message(999, True):
            pass
    assert error.value.status_code == 429
    now[0] = 3601
    with guard.message(999, True):
        pass
    assert guard.active == 0


def test_reservation_released_on_error_and_chat_limit():
    guard = PublicAccess(True, 'test-group-invitation')
    with pytest.raises(ValueError):
        with guard.message(1, True):
            raise ValueError('simulated database failure')
    assert guard.active == 0
    for _ in range(29):
        with guard.message(1, False):
            pass
    with pytest.raises(HTTPException) as error:
        with guard.message(1, False):
            pass
    assert error.value.status_code == 429
