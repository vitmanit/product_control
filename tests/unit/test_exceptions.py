from fastapi import status

from src.core.exceptions import (
    AppException,
    NotFoundError,
    ConflictError,
    ValidationError,
    BadRequestError,
)


def test_not_found_has_404():
    err = NotFoundError("batch")

    assert err.status_code == status.HTTP_404_NOT_FOUND
    assert err.detail == "batch"


def test_conflict_has_409():
    err = ConflictError()

    assert err.status_code == status.HTTP_409_CONFLICT


def test_validation_error_has_422():
    err = ValidationError("bad data")

    assert err.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert err.detail == "bad data"


def test_bad_request_has_400():
    err = BadRequestError()

    assert err.status_code == status.HTTP_400_BAD_REQUEST


def test_app_exception_is_http_exception():
    from fastapi import HTTPException

    assert issubclass(AppException, HTTPException)
