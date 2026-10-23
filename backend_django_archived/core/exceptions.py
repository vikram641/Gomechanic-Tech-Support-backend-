from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


def custom_exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is not None:
        return response

    # Anything DRF didn't already turn into a clean 4xx (e.g. a ValueError
    # raised from a repository function) becomes a generic 400 rather than
    # a raw 500 with a stack trace leaking to the client.
    return Response({"detail": str(exc)}, status=400)
