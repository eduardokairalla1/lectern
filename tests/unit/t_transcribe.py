"""
Unit tests for audio decoding, format detection and duration reading.
"""

# --- IMPORTS ---
from pathlib import Path
from src.config import config
from src.errors.invalid_request_error import InvalidRequestError
from src.errors.payload_too_large_error import PayloadTooLargeError
from src.errors.processing_error import ProcessingError
from src.errors.unsupported_media_type_error import UnsupportedMediaTypeError
from src.utils.transcribe import _read_audio_duration
from src.utils.transcribe import decode_audio
from src.utils.transcribe import get_audio_format

import base64
import pytest
import stat


# --- HELPERS ---
# smallest byte sequences filetype recognises, used to exercise the real
# detection instead of stubbing it
WAV_HEADER = b'RIFF\x00\x00\x00\x00WAVEfmt '
PNG_HEADER = b'\x89PNG\r\n\x1a\n' + b'\x00' * 24


@pytest.fixture
def fake_ffprobe(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Puts a scripted ffprobe first on PATH, so no binary is required."""

    def install(body: str) -> Path:
        script = tmp_path / 'ffprobe'
        script.write_text(body)
        script.chmod(script.stat().st_mode | stat.S_IEXEC)
        monkeypatch.setenv('PATH', str(tmp_path))
        return script

    return install


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


class TestReadAudioDuration:

    @pytest.mark.anyio
    async def test_parses_the_duration_ffprobe_reports(
        self, fake_ffprobe
    ) -> None:
        fake_ffprobe('#!/bin/sh\necho "12.345"\n')
        assert await _read_audio_duration(b'audio', 'wav') == 12.345

    @pytest.mark.anyio
    async def test_passes_a_file_with_the_right_extension(
        self, fake_ffprobe
    ) -> None:
        # ffprobe needs a seekable input with a usable suffix; the script
        # echoes the duration only when both hold
        fake_ffprobe(
            '#!/bin/sh\nfor last; do :; done\n'
            'case "$last" in *.webm) ;; *) exit 9;; esac\n'
            '[ -s "$last" ] || exit 9\necho "1.0"\n'
        )
        assert await _read_audio_duration(b'payload', 'webm') == 1.0

    @pytest.mark.anyio
    async def test_unreadable_audio_is_a_client_error(
        self, fake_ffprobe
    ) -> None:
        fake_ffprobe('#!/bin/sh\necho "moov atom not found" >&2\nexit 1\n')
        with pytest.raises(InvalidRequestError):
            await _read_audio_duration(b'audio', 'mp4')

    @pytest.mark.anyio
    async def test_missing_duration_metadata_is_a_client_error(
        self, fake_ffprobe
    ) -> None:
        fake_ffprobe('#!/bin/sh\necho "N/A"\n')
        with pytest.raises(InvalidRequestError):
            await _read_audio_duration(b'audio', 'ogg')

    @pytest.mark.anyio
    async def test_reads_the_duration_from_the_packets_when_the_header_lacks_it(
        self, fake_ffprobe
    ) -> None:
        # what every browser sends: MediaRecorder muxes WebM live and never
        # seeks back to write the Duration element, so the header says nothing
        # about a file that is perfectly good audio
        fake_ffprobe(
            '#!/bin/sh\n'
            'case "$*" in *packet=*) echo "6.960000,0.020000"\n'
            'echo "6.980000,0.020000";; *) echo "N/A";; esac\n'
        )
        assert await _read_audio_duration(b'audio', 'webm') == 7.0

    @pytest.mark.anyio
    async def test_does_not_scan_packets_when_the_header_has_a_duration(
        self, fake_ffprobe, tmp_path: Path
    ) -> None:
        # the packet scan walks the whole file; the cheap header read has to
        # stay the path that a normal upload takes
        marker = tmp_path / 'scanned'
        fake_ffprobe(
            '#!/bin/sh\n'
            f'case "$*" in *packet=*) touch {marker};; esac\n'
            'echo "12.345"\n'
        )
        assert await _read_audio_duration(b'audio', 'wav') == 12.345
        assert not marker.exists()

    @pytest.mark.anyio
    async def test_packets_without_timestamps_are_a_client_error(
        self, fake_ffprobe
    ) -> None:
        # nothing here can bound the length before paying the transcription
        fake_ffprobe(
            '#!/bin/sh\n'
            'case "$*" in *packet=*) echo "N/A,N/A";; *) echo "N/A";; esac\n'
        )
        with pytest.raises(InvalidRequestError):
            await _read_audio_duration(b'audio', 'webm')

    @pytest.mark.anyio
    async def test_missing_ffprobe_is_a_server_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # a broken host must not be reported to the visitor as their mistake
        monkeypatch.setenv('PATH', '/nonexistent')
        with pytest.raises(ProcessingError):
            await _read_audio_duration(b'audio', 'wav')

    @pytest.mark.anyio
    async def test_leaves_no_temporary_file_behind(
        self, fake_ffprobe, tmp_path: Path
    ) -> None:
        fake_ffprobe('#!/bin/sh\necho "1.0"\n')
        await _read_audio_duration(b'audio', 'wav')
        assert not list(Path('/tmp').glob('*.wav'))
