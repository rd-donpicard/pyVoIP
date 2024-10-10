from enum import Enum
from pyVoIP import regex
from pyVoIP.SIP.error import SIPParseError
from pyVoIP.SIP.message.parse import (
    parse_raw_headers,
    parse_message_for_body_parts,
    get_uri_header,
)
from pyVoIP.SIP.message.response_codes import ResponseCode
from pyVoIP.types import URI_HEADER
from typing import Any, Dict, List, Union, Tuple
import pyVoIP

__all__ = ["SIPMethod", "SIPMessage", "SIPRequest", "SIPResponse"]


debug = pyVoIP.debug


class SIPMethod(Enum):
    INVITE = "INVITE"
    ACK = "ACK"
    BYE = "BYE"
    CANCEL = "CANCEL"
    OPTIONS = "OPTIONS"
    NOTIFY = "NOTIFY"
    REGISTER = "REGISTER"
    MESSAGE = "MESSAGE"
    SUBSCRIBE = "SUBSCRIBE"
    REFER = "REFER"

    def __str__(self) -> str:
        return self._value_

    def __repr__(self) -> str:
        return str(self)


class SIPMessage:
    def __init__(
        self,
        start_line: List[str],
        headers: Dict[str, Any],
        body_parts: List[Tuple[str, Any]],
        authentication: Dict[str, Union[str, List[str]]],
        raw: bytes,
    ):
        self.start_line = start_line
        self.headers = headers
        self.authentication = authentication
        self.raw = raw
        self.body_parts = body_parts

        # Sadly this code uses "body" when it really means "sdp".
        # In order to support SIPREC (which has multiple body parts, including an sdp)
        # parse_message_for_body_parts returns a List[Typle(str, Any)].  We keep the list that comes
        # back, and we also try to find the SDP in the list and if so pass it along to
        # the derived class.  I did this really to maintain compatibility with the rest of the
        # code in this package (which kinda all require that the body is the sdp if there is one)
        sdp_tuple = next((t for t in body_parts if t[0] == "application/sdp"), None)
        if sdp_tuple:
            self.body = sdp_tuple[1]
        else:
            self.body = {'content': None}

    def summary(self) -> str:
        data = ""
        data += f"{' '.join(self.start_line)}\n\n"
        data += "Headers:\n"
        for x in self.headers:
            data += f"{x}: {self.headers[x]}\n"
        data += "\n"
        data += "Body:\n"
        for x in self.body:
            data += f"{x}: {self.body[x]}\n"
        data += "\n"
        data += "All Body Parts:\n"
        data += str(self.body_parts)

        return data

    @staticmethod
    def from_bytes(data: bytes) -> Union["SIPRequest", "SIPResponse"]:
        parsed_headers: Dict[str, Any] = {"Via": []}
        parsed_body: Dict[str, Any] = {}
        authentication: Dict[str, Union[str, List[str]]] = {}
        version_match = regex.SIP_VERSION_MATCH

        try:
            try:
                headers, body = data.split(b"\r\n\r\n", maxsplit=1)
            except ValueError as ve:
                debug(f"Error unpacking data, only using headers. ({ve})")
                headers = data
                body = b""

            headers_raw = headers.split(b"\r\n")
            start_line = str(headers_raw.pop(0), "utf8").split(" ")
            check = start_line[0]

            response = False

            if version_match.match(check):
                if check.upper() not in pyVoIP.SIPCompatibleVersions:
                    raise SIPParseError(f"SIP Version {check} not compatible.")

                response = True
                status = ResponseCode(int(start_line[1]))
            else:
                if start_line[2].upper() not in pyVoIP.SIPCompatibleVersions:
                    raise SIPParseError(
                        f"SIP Version {start_line[2]} not compatible."
                    )
                if start_line[0] not in map(lambda x: str(x), list(SIPMethod)):
                    raise SIPParseError(
                        f"SIP Method `{start_line[0]}` not supported."
                    )

                method = SIPMethod(start_line[0])
                destination = get_uri_header(start_line[1])

            parsed_headers = parse_raw_headers(headers_raw)

            authentication = {}
            if "WWW-Authenticate" in parsed_headers:
                authentication = parsed_headers["WWW-Authenticate"]
            elif "Authorization" in parsed_headers:
                authentication = parsed_headers["Authorization"]
            elif "Proxy-Authenticate" in parsed_headers:
                authentication = parsed_headers["Proxy-Authenticate"]

            # We have to send in the entire message because a multipart body
            # has the boundary defined in the header
            body_parts = parse_message_for_body_parts(data)

            if response:
                return SIPResponse(
                    start_line,
                    parsed_headers,
                    body_parts,
                    authentication,
                    data,
                    status,
                )
            return SIPRequest(
                start_line,
                parsed_headers,
                body_parts,
                authentication,
                data,
                method,
                destination,
            )

        except Exception as e:
            if type(e) is not SIPParseError:
                raise SIPParseError(e) from e
            raise

    @staticmethod
    def from_string(data: str) -> Union["SIPRequest", "SIPResponse"]:
        try:
            return SIPMessage.from_bytes(data.encode("utf8"))
        except Exception as e:
            if type(e) is not SIPParseError:
                raise SIPParseError(e) from e
            raise


class SIPRequest(SIPMessage):
    def __init__(
        self,
        start_line: List[str],
        headers: Dict[str, Any],
        body: Dict[str, Any],
        authentication: Dict[str, Union[str, List[str]]],
        raw: bytes,
        method: SIPMethod,
        destination: URI_HEADER,
    ):
        super().__init__(start_line, headers, body, authentication, raw)
        self.method = method
        self.destination = destination

    @property
    def destination(self) -> URI_HEADER:
        """
        The destination property specifies the Request-URI in the Request-Line
        detailed in RFC 3261 Section 7.1
        """
        return self._destination

    @destination.setter
    def destination(self, value: URI_HEADER) -> None:
        self._destination = value


class SIPResponse(SIPMessage):
    def __init__(
        self,
        start_line: List[str],
        headers: Dict[str, Any],
        body: Dict[str, Any],
        authentication: Dict[str, Union[str, List[str]]],
        raw: bytes,
        status: ResponseCode,
    ):
        super().__init__(start_line, headers, body, authentication, raw)
        self.status = status
