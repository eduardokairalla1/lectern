"""
Unit tests for audio decoding, format detection and duration reading.
"""

# --- IMPORTS ---
from src.config import config
from src.errors.invalid_request_error import InvalidRequestError
from src.errors.payload_too_large_error import PayloadTooLargeError
from src.errors.unsupported_media_type_error import UnsupportedMediaTypeError
from src.utils.transcribe import decode_audio
from src.utils.transcribe import get_audio_format

import base64
import pytest


# --- HELPERS ---
# smallest byte sequences filetype recognises, used to exercise the real
# detection instead of stubbing it
WAV_HEADER = b'RIFF\x00\x00\x00\x00WAVEfmt '
PNG_HEADER = b'\x89PNG\r\n\x1a\n' + b'\x00' * 24

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


class TestGetAudioFormat:

    def test_detects_a_supported_container(self) -> None:
        assert get_audio_format(WAV_HEADER) == 'wav'

    def test_rejects_bytes_it_cannot_identify(self) -> None:
        with pytest.raises(InvalidRequestError):
            get_audio_format(b'\x00\x01\x02\x03')

    def test_rejects_empty_bytes(self) -> None:
        with pytest.raises(InvalidRequestError):
            get_audio_format(b'')

    def test_rejects_a_recognised_but_unsupported_format(self) -> None:
        with pytest.raises(UnsupportedMediaTypeError):
            get_audio_format(PNG_HEADER)

