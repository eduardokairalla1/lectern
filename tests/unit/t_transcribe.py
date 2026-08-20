"""
Unit tests for audio decoding, format detection and duration reading.
"""

# --- IMPORTS ---
from src.config import config
from src.errors.invalid_request_error import InvalidRequestError
from src.errors.payload_too_large_error import PayloadTooLargeError
from src.utils.transcribe import decode_audio

import base64
import pytest


# --- CODE ---
class TestDecodeAudio:

    def test_decodes_valid_base64(self) -> None:
        assert decode_audio(base64.b64encode(b'audio').decode()) == b'audio'

    def test_empty_payload_decodes_to_empty_bytes(self) -> None:
        assert decode_audio('') == b''

    def test_rejects_invalid_base64(self) -> None:
        with pytest.raises(InvalidRequestError):
            decode_audio('not base64!!')

    def test_rejects_a_payload_over_the_size_limit(self) -> None:
        # the limit is on the decoded bytes, which are 3/4 of the base64
        oversized = b'x' * (int(config.MAX_AUDIO_BASE64_SIZE * 3 / 4) + 10)
        with pytest.raises(PayloadTooLargeError):
            decode_audio(base64.b64encode(oversized).decode())

    def test_accepts_a_payload_at_the_limit(self) -> None:
        at_limit = b'x' * int(config.MAX_AUDIO_BASE64_SIZE * 3 / 4)
        assert len(decode_audio(base64.b64encode(at_limit).decode())) == len(
            at_limit
        )

