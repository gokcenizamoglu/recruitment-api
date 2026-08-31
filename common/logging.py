import contextvars
import logging

request_id_context = contextvars.ContextVar("request_id", default="-")


class RequestIDFilter(logging.Filter):
    def filter(self, record):
        record.request_id = request_id_context.get()
        return True
