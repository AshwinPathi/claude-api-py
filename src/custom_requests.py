"""Home made requests library with urllib since this helps bypass Claude API protections.

Note that the |header| parameter for all these methods are required.
"""
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import json
from typing import Dict, Any, Optional, Union, List, Iterator
from dataclasses import dataclass
import sseclient

JsonType = Union[str, int, float, bool, None, Dict[str, Any], List[Any]]
HeaderType = Dict[str, str]


@dataclass
class Response:
    """Wrapper for the return type for all custom requests methods.
    Acts as a loose wrapper around requests.Response.
    """

    ok: bool
    data: Union[bytes, str]

    def json(self) -> JsonType:
        if isinstance(self.data, str):
            return json.loads(self.data)
        elif isinstance(self.data, bytes):
            return json.loads(self.data.decode("utf-8"))
        else:
            raise RuntimeError("Decoding non-str or bytes type.")


def get(url: str, headers: HeaderType) -> Response:
    """Public method for a GET Request."""
    return _custom_requests_get(url, headers=headers)


def post(
    url: str, headers: HeaderType, request_body: Optional[JsonType] = None
) -> Response:
    """Public method for a POST Request."""
    return _custom_requests_post(url, headers=headers, request_body=request_body)


def sse(
    url: str, headers: HeaderType, request_body: Optional[JsonType] = None
) -> Iterator[str]:
    """Public method for a POST request that requires SSE."""
    for streamed_data in _custom_requests_sse(
        url, headers=headers, request_body=request_body
    ):
        yield streamed_data


def delete(url: str, headers: HeaderType) -> Response:
    """Public method for a DELETE request."""
    return _custom_requests_delete(url, headers=headers)


def _custom_requests_get(url: str, headers: HeaderType) -> Response:
    """Private method wrapper for GET requests to a URL."""
    request = Request(url)
    for header_key, header_value in headers.items():
        request.add_header(header_key, header_value)

    return _safe_request_read(request)


def _custom_requests_post(
    url: str, headers: HeaderType, request_body: Optional[JsonType] = None
) -> Response:
    """Private method wrapper for POST requests to a URL."""
    request = Request(url, method="POST")
    for header_key, header_value in headers.items():
        request.add_header(header_key, header_value)

    if request_body is None:
        return _safe_request_read(request)

    encoded_request_body = json.dumps(request_body).encode()
    return _safe_request_read(request, data=encoded_request_body)


def _custom_requests_sse(
    url: str, headers: HeaderType, request_body: Optional[JsonType] = None
) -> Iterator[str]:
    """Helper method for streaming SSE responses."""

    request = Request(url, method="POST")
    for header_key, header_value in headers.items():
        request.add_header(header_key, header_value)

    encoded_request_body = json.dumps(request_body).encode()
    try:
        response = urlopen(request, data=encoded_request_body)
        client = sseclient.SSEClient(response)
        for event in client.events():
            yield event.data
    except (HTTPError, URLError) as e:
        print(e)


def _custom_requests_delete(url: str, headers: HeaderType) -> Response:
    """Helper method for calling HTTP delete."""
    request = Request(url, method="DELETE")
    for header_key, header_value in headers.items():
        request.add_header(header_key, header_value)

    return _safe_request_read(request)


def _safe_request_read(request: Request, data: Optional[bytes] = None) -> Response:
    """Read a request with some data and return the response."""
    if data is not None:
        try:
            with urlopen(request, data=data) as response:
                return Response(ok=True, data=response.read())
        except (HTTPError, URLError) as e:
            print(e)
            return Response(ok=False, data=b"")
    try:
        with urlopen(request) as response:
            return Response(ok=True, data=response.read())
    except (HTTPError, URLError) as e:
        print(e)
        return Response(ok=False, data=b"")
