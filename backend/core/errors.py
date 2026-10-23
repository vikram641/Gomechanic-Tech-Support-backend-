"""Error handling that preserves the DRF-shaped wire contract documented in
docs/API.md: field-level validation errors as {"field_name": ["message"]},
everything else as {"detail": "message"}.
"""

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Raise for business-logic errors (duplicate email, bad state
    transition, etc). If `field` is set, the response is shaped like a DRF
    serializer field error; otherwise it's a generic {"detail": ...}."""

    def __init__(self, message: str, field: str | None = None, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.field = field
        self.status_code = status_code


async def app_error_handler(request: Request, exc: AppError):
    if exc.field:
        return JSONResponse({exc.field: [exc.message]}, status_code=exc.status_code)
    return JSONResponse({"detail": exc.message}, status_code=exc.status_code)


async def http_exception_handler(request: Request, exc: HTTPException):
    detail = exc.detail
    if isinstance(detail, (dict, list)):
        return JSONResponse(detail, status_code=exc.status_code, headers=exc.headers)
    return JSONResponse({"detail": detail}, status_code=exc.status_code, headers=exc.headers)


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Reshape Pydantic's default {"detail": [{"loc":..., "msg":...}]} into
    DRF's {"field_name": ["message"]}, at 400 instead of FastAPI's default
    422, to match docs/API.md's documented error contract."""
    errors: dict[str, list[str]] = {}
    for error in exc.errors():
        loc = error.get("loc", ())
        field = str(loc[-1]) if loc else "detail"
        errors.setdefault(field, []).append(error.get("msg", "Invalid value."))
    return JSONResponse(errors, status_code=400)


def register_exception_handlers(app):
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
