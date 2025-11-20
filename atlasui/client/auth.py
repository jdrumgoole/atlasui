"""
Authentication handlers for MongoDB Atlas API.
"""

import httpx
from typing import Generator


class DigestAuth(httpx.Auth):
    """
    HTTP Digest Authentication for MongoDB Atlas API.

    Atlas API uses HTTP Digest Authentication with username (public key)
    and password (private key).
    """

    def __init__(self, username: str, password: str) -> None:
        """
        Initialize Digest Auth.

        Args:
            username: Atlas public API key
            password: Atlas private API key
        """
        self.username = username
        self.password = password

    def auth_flow(self, request: httpx.Request) -> Generator[httpx.Request, httpx.Response, None]:
        """
        Implement HTTP Digest Authentication flow.

        Args:
            request: The outgoing HTTP request

        Yields:
            Authenticated requests
        """
        # Try initial request
        response = yield request

        # If we get a 401, handle the digest challenge
        if response.status_code == 401:
            # Create a new request with the same properties
            auth_request = httpx.Request(
                method=request.method,
                url=request.url,
                headers=request.headers.copy(),
                content=request.content,
            )

            # Parse the WWW-Authenticate header
            if "www-authenticate" in response.headers:
                # Create digest authentication response
                from hashlib import md5
                import re
                import secrets

                auth_header = response.headers["www-authenticate"]

                # Extract digest parameters
                realm_match = re.search(r'realm="([^"]*)"', auth_header)
                nonce_match = re.search(r'nonce="([^"]*)"', auth_header)
                qop_match = re.search(r'qop="([^"]*)"', auth_header)

                if realm_match and nonce_match:
                    realm = realm_match.group(1)
                    nonce = nonce_match.group(1)
                    qop = qop_match.group(1) if qop_match else None

                    # Generate digest response
                    uri = str(request.url.raw_path)
                    method = request.method

                    ha1 = md5(f"{self.username}:{realm}:{self.password}".encode()).hexdigest()
                    ha2 = md5(f"{method}:{uri}".encode()).hexdigest()

                    if qop:
                        nc = "00000001"
                        cnonce = secrets.token_hex(8)
                        response_hash = md5(
                            f"{ha1}:{nonce}:{nc}:{cnonce}:{qop}:{ha2}".encode()
                        ).hexdigest()

                        auth_value = (
                            f'Digest username="{self.username}", '
                            f'realm="{realm}", '
                            f'nonce="{nonce}", '
                            f'uri="{uri}", '
                            f'qop={qop}, '
                            f'nc={nc}, '
                            f'cnonce="{cnonce}", '
                            f'response="{response_hash}"'
                        )
                    else:
                        response_hash = md5(f"{ha1}:{nonce}:{ha2}".encode()).hexdigest()
                        auth_value = (
                            f'Digest username="{self.username}", '
                            f'realm="{realm}", '
                            f'nonce="{nonce}", '
                            f'uri="{uri}", '
                            f'response="{response_hash}"'
                        )

                    auth_request.headers["Authorization"] = auth_value
                    yield auth_request
