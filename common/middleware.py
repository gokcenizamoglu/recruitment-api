import uuid

from common.logging import request_id_context


class RequestIDMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))[:64]
        token = request_id_context.set(request_id)
        request.request_id = request_id
        try:
            response = self.get_response(request)
            response["X-Request-ID"] = request_id
            return response
        finally:
            request_id_context.reset(token)
