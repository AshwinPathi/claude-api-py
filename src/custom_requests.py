"""Home made barebones requests library with urllib since this helps bypass 
Claude API protections.
"""
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from typing import Dict, Any, Optional, Union, List, Iterator
from dataclasses import dataclass
import json

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
    request = Request(url)
    for header_key, header_value in headers.items():
        request.add_header(header_key, header_value)

    return _safe_request_read(request)


def post(
    url: str, headers: HeaderType, request_body: Optional[JsonType] = None
) -> Response:
    """Public method for a POST Request."""
    request = Request(url, method="POST")
    for header_key, header_value in headers.items():
        request.add_header(header_key, header_value)

    if request_body is None:
        return _safe_request_read(request)

    encoded_request_body = json.dumps(request_body).encode()
    return _safe_request_read(request, data=encoded_request_body)


def sse(
    url: str, headers: HeaderType, request_body: Optional[JsonType] = None
) -> Iterator[str]:
    """Public method for a POST request that requires SSE."""
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


def delete(url: str, headers: HeaderType) -> Response:
    """Public method for a DELETE request."""
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
