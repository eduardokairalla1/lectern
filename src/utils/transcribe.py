"""
Audio transcription helper.
"""

# --- IMPORTS ---
from src.config import config
from src.errors.invalid_request_error import InvalidRequestError
from src.errors.payload_too_large_error import PayloadTooLargeError
from src.errors.processing_error import ProcessingError
from src.errors.unsupported_media_type_error import UnsupportedMediaTypeError
from tempfile import NamedTemporaryFile

import asyncio
import base64
import filetype
import logging


# --- GLOBALS ---
logger = logging.getLogger(__name__)


# --- CODE ---
async def _read_audio_duration(audio_bytes: bytes, ext: str) -> float:
    """
    Read the audio duration from the container metadata, using ffprobe.

    :param audio_bytes: Decoded audio bytes.
    :param ext: Audio format extension.

    :raises ProcessingError: If ffprobe is missing from the host.
    :raises InvalidRequestError: If the audio can't be read.

    :return: Audio duration in seconds.
    """
    # write the audio bytes to a temporary file with the correct extension
    with NamedTemporaryFile(suffix=f'.{ext}') as tmp:

        # writing a multi-MB payload is blocking: keep it off the event loop
        await asyncio.to_thread(tmp.write, audio_bytes)
        tmp.flush()

        # ask ffprobe for the duration alone
        try:
            process = await asyncio.create_subprocess_exec(
                'ffprobe',
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                tmp.name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

        # ffprobe is not installed: log and raise
        except FileNotFoundError as e:
            logger.error('Audio duration check failed: ffprobe not found.')
            raise ProcessingError({'error': 'ffprobe is not available'}) from e

    # ffprobe rejected the file: it is corrupt or not really audio
    if process.returncode != 0:
        logger.error(
            f'Transcription failed: unreadable audio. '
            f'ffprobe: {stderr.decode().strip()}'
        )
        raise InvalidRequestError()

    # parse the duration from ffprobe's output
    try:
        return float(stdout.decode().strip())

    # ffprobe output is not a valid float: log and raise
    except ValueError as e:
        logger.error(
            f'Transcription failed: audio carries no duration ({ext}).'
        )
        raise InvalidRequestError() from e


async def _validate_audio_duration(audio_bytes: bytes, ext: str) -> None:
    """
    Validate the audio duration against the configured maximum.

    :param audio_bytes: Decoded audio bytes.
    :param ext: Audio format extension.

    :raises InvalidRequestError: If the audio is too long or can't be read.

    :return: None
    """
    # read the audio duration
    duration_seconds = await _read_audio_duration(audio_bytes, ext)

    # audio duration exceeds the maximum allowed: log and raise
    if duration_seconds > config.MAX_AUDIO_DURATION_SECONDS:
        logger.warning(
            f'Transcription failed: Audio too long. '
            f'Duration: {duration_seconds:.1f}s, '
            f'Max: {config.MAX_AUDIO_DURATION_SECONDS}s'
        )
        raise InvalidRequestError()

    # log the validated audio duration
    logger.info(f'Audio duration validated: {duration_seconds:.1f}s')


def decode_audio(media_base64: str) -> bytes:
    """
    Decode the base64 audio payload and validate the decoded size.

    :param media_base64: Base64 string of the audio file.

    :raises InvalidRequestError: If the base64 data is invalid.
    :raises PayloadTooLargeError: If the decoded audio exceeds the size limit.

    :return: Decoded audio bytes.
    """

    # decode base64 audio data
    try:
        audio_bytes = base64.b64decode(media_base64, validate=True)

    # invalid base64 data: log and raise
    except Exception as e:
        logger.error(
            f'Transcription failed: Invalid base64 audio data. Error: {str(e)}'
        )
        raise InvalidRequestError() from e

    # calculate the maximum allowed size of the decoded audio in bytes
    max_decoded_bytes = (config.MAX_AUDIO_BASE64_SIZE * 3) / 4

    # decoded audio exceeds the maximum allowed size: log and raise
    if len(audio_bytes) > max_decoded_bytes:

        # calculate size in MB
        actual_mb = len(audio_bytes) / (1024 * 1024)
        max_decoded_mb = max_decoded_bytes / (1024 * 1024)

        # log the error and raise
        logger.error(
            f'Transcription failed: Decoded audio too large. '
            f'Size: {actual_mb:.2f}MB, Max: {max_decoded_mb:.1f}MB'
        )
        raise PayloadTooLargeError()

    # return the decoded audio bytes
    return audio_bytes


def get_audio_format(audio_bytes: bytes) -> str:
    """
    Detect the audio format and validate it against supported formats.

    :param audio_bytes: Decoded audio bytes.

    :raises InvalidRequestError: If the format can't be detected.
    :raises UnsupportedMediaTypeError: If the format isn't supported.

    :return: File extension of the detected format.
    """
    # detect the audio format
    kind = filetype.guess(audio_bytes)

    # format can't be detected: log and raise
    if not kind:
        logger.error(
            'Transcription failed: Unable to detect audio file format. '
            'File may be corrupted.'
        )
        raise InvalidRequestError()

    # format isn't supported: log and raise
    if kind.extension not in config.AUDIO_SUPPORTED_FORMATS:
        logger.error(
            f'Transcription failed: Unsupported audio format '
            f'"{kind.extension}". Supported: {config.AUDIO_SUPPORTED_FORMATS}'
        )
        raise UnsupportedMediaTypeError()

    # return the detected audio format extension
    return kind.extension

