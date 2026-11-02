"""Outbound HTTP transport that never forwards credentials through redirects."""

from urllib.request import HTTPRedirectHandler, build_opener


class NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_opener = build_opener(NoRedirectHandler())


def open_service(request, *, timeout):
    return _opener.open(request, timeout=timeout)
