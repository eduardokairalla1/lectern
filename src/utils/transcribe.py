"""
Audio transcription helper.
"""

# --- IMPORTS ---
from src.config import config
from src.errors.invalid_request_error import InvalidRequestError
from src.errors.payload_too_large_error import PayloadTooLargeError
from src.errors.unsupported_media_type_error import UnsupportedMediaTypeError

import base64
import filetype
import logging


# --- GLOBALS ---
logger = logging.getLogger(__name__)


# --- CODE ---
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

