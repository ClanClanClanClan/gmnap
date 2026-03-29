"""
Mock implementations for optional dependencies.
These allow the system to run without external dependencies while maintaining API compatibility.
"""

import logging

logger = logging.getLogger(__name__)


class MockPyJWT:
    """Mock implementation of PyJWT for authentication."""

    @staticmethod
    def encode(payload, secret, algorithm="HS256"):
        """Mock JWT encoding."""
        logger.debug("Using mock JWT encoding")
        # Return a fake but consistent token
        import base64
        import json

        header = {"alg": algorithm, "typ": "JWT"}
        header_b64 = base64.b64encode(json.dumps(header).encode()).decode().rstrip("=")
        payload_b64 = base64.b64encode(json.dumps(payload).encode()).decode().rstrip("=")
        signature = base64.b64encode(b"mock-signature").decode().rstrip("=")
        return f"{header_b64}.{payload_b64}.{signature}"

    @staticmethod
    def decode(token, secret, algorithms=["HS256"], options=None):
        """Mock JWT decoding."""
        logger.debug("Using mock JWT decoding")
        # Parse the mock token
        try:
            parts = token.split(".")
            if len(parts) != 3:
                raise ValueError("Invalid token format")
            import base64
            import json

            # Add padding if needed
            payload_b64 = parts[1] + "=" * (4 - len(parts[1]) % 4)
            payload = json.loads(base64.b64decode(payload_b64))
            return payload
        except Exception as e:
            raise ValueError(f"Mock JWT decode error: {e}")


class MockPynini:
    """Mock implementation of Pynini for FST operations."""

    class Fst:
        """Mock FST class."""

        def __init__(self):
            self.data = {}

        @classmethod
        def read(cls, path):
            """Mock FST read from file."""
            logger.debug(f"Mock reading FST from {path}")
            fst = cls()
            # Return empty FST that won't match anything
            return fst

        def __call__(self, input_str):
            """Mock FST application."""
            return None

        def num_states(self):
            """Mock number of states."""
            return 0

    @staticmethod
    def accep(string, token_type=None):
        """Mock acceptor creation."""
        return MockPynini.Fst()

    @staticmethod
    def compose(a, b):
        """Mock FST composition."""
        return MockPynini.Fst()

    @staticmethod
    def concat(a, b):
        """Mock FST concatenation."""
        return MockPynini.Fst()

    @staticmethod
    def project(fst, direction):
        """Mock FST projection."""
        return fst

    @staticmethod
    def shortestpath(fst, nshortest=1, unique=True):
        """Mock shortest path."""
        return MockPynini.Fst()

    class FstOpError(Exception):
        """Mock FST operation error."""

        pass


def get_jwt_module():
    """Get JWT module (real or mock)."""
    try:
        import jwt

        return jwt
    except ImportError:
        logger.warning("PyJWT not installed, using mock implementation")
        return MockPyJWT()


def get_pynini_module():
    """Get Pynini module (real or mock)."""
    try:
        import pynini

        return pynini
    except ImportError:
        logger.warning("Pynini not installed, using mock implementation")
        return MockPynini()
