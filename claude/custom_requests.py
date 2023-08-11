"""Home made barebones requests library with urllib since this helps bypass 
Claude API protections.
"""
from dataclasses import dataclass
import uuid
import io
import json
import mimetypes
from typing import Optional, Union, Iterator, Tuple
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

import sseclient

from claude.custom_types import JsonType, HeaderType, FormDataType
from claude import logger


####################################################################
#                                                                  #
#                         Helper Classes                           #
#                                                                  #
####################################################################

# Carriage return/line feed separator
CRLF = "\r\n"


@dataclass
class Response:
    """Wrapper for the return type for all custom requests methods.
    Acts as a loose wrapper around requests.Response.
    """

    ok: bool
    data: Union[bytes, str]
    status_code: Optional[int]
    error: Optional[str]

    def json(self) -> JsonType:
        if isinstance(self.data, str):
            return json.loads(self.data)
        elif isinstance(self.data, bytes):
            return json.loads(self.data.decode("utf-8"))
        else:
            raise RuntimeError("Decoding non-str or bytes type.")


class FormData:
    """Since I'm doing this without the requests library, I also need to implement multipart
    file uploads with urllib. This class basically reconstructs the binary encoded FormData
    field thats sent in the request body of a POST request.

    Implementation inspired by this post:
    https://stackoverflow.com/questions/680305/using-multipartposthandler-to-post-form-data-with-python
    """

    def __init__(self, form_data: Optional[FormDataType] = None):
        """Initialize with a dicionary of form field information, similar to how you would
        use it for the requests library when passing in a file.

        ex.
        files = {
            "orgUuid": organization_uuid,
            "file": (file_path, open(file_path, 'rb')), # note that you have to open the file in BINARY mode
        }
        """
        self._fields = {}
        self._files = {}
        if form_data is not None:
            for key, value in form_data.items():
                if isinstance(value, str):
                    self._fields[key] = value
                elif isinstance(value, tuple) and len(value) == 2:
                    self._files[key] = value
                else:
                    raise RuntimeError(
                        "Incorrect constructor type during form data initialization."
                    )

    def add_field(self, key: str, value: str) -> None:
        """Add an additional named field to the fields struct."""
        self._fields[key] = value

    def add_file(
        self, field_name: str, file_name: str, file_open: io.BufferedReader
    ) -> None:
        """Add an additional file to the field struct. Note that the |file_open| should be
        a call to open(file_name, 'rb').
        """
        self._files[field_name] = (file_name, file_open)

    def encode(self) -> Tuple[str, bytes]:
        """Turn the form fields into a request body to send over requests."""
        generated_boundary = f"{self._generate_boundary()}"
        boundary_segment = f"--{generated_boundary}"

        stream = io.BytesIO()
        needsCRLF = False
        # Add fields to the form.
        for key, value in self._fields.items():
            if needsCRLF:
                stream.write(CRLF.encode())
            needsCRLF = True
            field_header = f'content-disposition: form-data; name="{key}"'
            stream.write(
                CRLF.join([boundary_segment, field_header, "", value]).encode()
            )

        # Add files to the form.
        for field_name, (file_name, file_open) in self._files.items():
            if needsCRLF:
                stream.write(CRLF.encode())
            needsCRLF = True
            field_header = f'content-disposition: form-data; name="{field_name}"; filename="{file_name}"'
            content_type = (
                mimetypes.guess_type(file_name)[0] or "application/octet-stream"
            )
            content_type_header = f"content-type: {content_type}"
            stream.write(
                CRLF.join(
                    [boundary_segment, field_header, content_type_header, ""]
                ).encode()
            )
            stream.write(CRLF.encode())
            with file_open as f:
                stream.write(f.read())

        # Footer
        stream.write(f"{CRLF}--{generated_boundary}--{CRLF}".encode())
        # Return the content type.
        content_type = f"multipart/form-data; boundary={generated_boundary}"
        return content_type, stream.getvalue()

    def _generate_boundary(self) -> str:
        """Genarates a unique boundary per call. For now this is just a uuid, it doesn't need to be
        anything special.
        """
        return str(uuid.uuid4()).replace("-", "")


####################################################################
#                                                                  #
#                     Core Request Methods                         #
#                                                                  #
####################################################################


def post_form_data(url: str, headers: HeaderType, files: FormDataType) -> Response:
    """Wrapper function to send over a form data over POST request."""
    form_data_obj = FormData(files)
    content_type, encoded_request_body = form_data_obj.encode()
    # Don't modify the passed in header.
    header_copy = headers.copy()
    # Transparently add the content type and content length header information
    # based on the information we decoded.
    header_copy.update({"content-type": content_type})
    header_copy.update({"content-length": str(len(encoded_request_body))})
    return post(url, headers=header_copy, request_body=encoded_request_body)


def get(url: str, headers: HeaderType) -> Response:
    """Public method for a GET Request."""
    logger.logger.info("Sending GET request to: %s with headers: %s", url, str(headers))
    request = Request(url)
    for header_key, header_value in headers.items():
        request.add_header(header_key, header_value)

    return _safe_request_read(request)


def post(
    url: str, headers: HeaderType, request_body: Optional[Union[JsonType, bytes]] = None
) -> Response:
    """Public method for a POST Request."""
    logger.logger.info("Sending POST request to: %s with headers: %s", url, str(headers))
    request = Request(url, method="POST")
    for header_key, header_value in headers.items():
        request.add_header(header_key, header_value)


    encoded_request_body = None
    if request_body is not None:
        logger.logger.info("POST request body is non-empty.")
        if isinstance(request_body, bytes):
            logger.logger.info("POST request body is bytes type.")
            encoded_request_body = request_body
        elif isinstance(request_body, str):
            logger.logger.info("POST request body is string type, encoding.")
            encoded_request_body = request_body.encode()
        else:
            logger.logger.info("POST request body is JSON type, dumping then encoding.")
            encoded_request_body = json.dumps(request_body).encode()
    return _safe_request_read(request, data=encoded_request_body)


def sse(
    url: str, headers: HeaderType, request_body: Optional[JsonType] = None
) -> Iterator[str]:
    """Public method for a POST request that requires SSE."""
    logger.logger.info("Sending SSE POST request to: %s with headers: %s", url, str(headers))
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
        logger.logger.info("SEE POST failed with error: %s", str(e))
        print(e)


def delete(url: str, headers: HeaderType) -> Response:
    """Public method for a DELETE request."""
    logger.logger.info("Sending DELETE request to: %s with headers: %s", url, str(headers))
    request = Request(url, method="DELETE")
    for header_key, header_value in headers.items():
        request.add_header(header_key, header_value)

    return _safe_request_read(request)


def _safe_request_read(request: Request, data: Optional[bytes] = None) -> Response:
    """Read a request with some data and return the response. Handles packaging
    the response in a Response Wrapper object.
    """
    status_code = None
    try:
        with urlopen(request, data=data) as response:
            status_code = response.getcode()
            return Response(ok=True, data=response.read(), status_code=status_code, error=None)
    except (HTTPError, URLError) as e:
        return Response(ok=False, data=b"", status_code=status_code, error=str(e))
