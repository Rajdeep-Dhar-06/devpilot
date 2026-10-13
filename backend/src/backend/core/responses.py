from typing import TypeVar
from fastapi.responses import JSONResponse
from backend.schemas.common import ApiError, ApiResponse

T = TypeVar("T")

def success_response(data):
    return {
        "success": True,
        "data": data,
        "error": None,
    }


def error_response(code, message):
    return {
        "success": False,
        "data": None,
        "error": {
            "code": code,
            "message": message,
        },
    }

# def success_response(data: T) -> ApiResponse[T]:
#     return ApiResponse(
#         success=True,
#         data=data,
#         error=None,
#     )

# def error_response(
#     status_code: int,
#     code: str,
#     message: str,
# ) -> JSONResponse:
#     response = ApiResponse[None](
#         success=False,
#         data=None,
#         error=ApiError(
#             code=code,
#             message=message,
#         ),
#     )

#     return JSONResponse(
#         status_code=status_code,
#         content=response.model_dump(mode="json"),
#     )