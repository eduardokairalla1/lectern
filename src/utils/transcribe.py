"""
Audio transcription helper.
"""

# --- IMPORTS ---
from io import BytesIO
from openai import omit
from src.clients.llms import TRANSCRIBE_LLM
from src.config import config
from src.errors.invalid_request_error import InvalidRequestError
from src.errors.payload_too_large_error import PayloadTooLargeError
from src.errors.processing_error import ProcessingError
from src.errors.transcription_error import TranscriptionError
from src.errors.unsupported_media_type_error import UnsupportedMediaTypeError
from tempfile import NamedTemporaryFile

import asyncio
import base64
import filetype
import logging


# --- GLOBALS ---
logger = logging.getLogger(__name__)


# --- CODE ---
def _parse_seconds(value: str) -> float | None:
    """
    Parse one timestamp from ffprobe's output.

    :param value: A single ffprobe field.

    :return: The value in seconds, or None when ffprobe printed 'N/A' or
        anything else that is not a number.
    """
    # parse the value as a float
    try:
        return float(value.strip())

    # parsing failed: return None
    except ValueError:
        return None


def _last_packet_end(csv: str) -> float | None:
    """
    Derive the duration from the end timestamp of the last audio packet.

    :param csv: ffprobe's packet listing, as 'pts_time,duration_time' rows.

    :return: The end timestamp of the last usable packet, or None when the
        listing carries no timestamp at all.
    """
    # iterate over the rows in reverse order
    for row in reversed(csv.strip().splitlines()):

        # parse the start timestamp and duration of the packet
        fields = row.split(',')
        start = _parse_seconds(fields[0])

        # start timestamp is missing: skip this packet and keep looking
        if start is None:
            continue

        # duration is present: return the end timestamp of this packet
        length = _parse_seconds(fields[1]) if len(fields) > 1 else None
        return start + (length or 0.0)

    # no packet carried a timestamp: return None
    return None


async def _probe(path: str, *args: str) -> str:
    """
    Run ffprobe over a file and return its stdout.

    :param path: Path to the audio file.
    :param args: The ffprobe arguments describing what to read.

    :raises ProcessingError: If ffprobe is missing from the host.
    :raises InvalidRequestError: If ffprobe rejected the file.

    :return: ffprobe's stdout, decoded.
    """
    # run ffprobe in a subprocess and capture its stdout and stderr
    try:
        process = await asyncio.create_subprocess_exec(
            'ffprobe', '-v', 'error', *args, path,
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
        raise InvalidRequestError({'reason': 'unreadable_audio'})

    # return the decoded stdout
    return stdout.decode()


async def _read_audio_duration(audio_bytes: bytes, ext: str) -> float:
    """
    Read the audio duration, using ffprobe.

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

        # probe the file for its declared duration
        declared = _parse_seconds(await _probe(
            tmp.name,
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
        ))
        if declared is not None and declared > 0:
            return declared

        # ffprobe did not declare a duration: read the last packet's
        # end timestamp
        logger.debug(
            f'Container declares no duration ({ext}): '
            f'reading it from the packet timestamps.'
        )
        measured = _last_packet_end(await _probe(
            tmp.name,
            '-select_streams', 'a:0',
            '-show_entries', 'packet=pts_time,duration_time',
            '-of', 'csv=p=0',
        ))

    # ffprobe did not report any usable packet timestamps: log and raise
    if measured is None or measured <= 0:
        logger.error(
            f'Transcription failed: audio carries no duration ({ext}).'
        )
        raise InvalidRequestError({'reason': 'undeterminable_duration'})

    # return the measured duration
    return measured


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
        raise InvalidRequestError({
            'reason': 'audio_too_long',
            'duration_seconds': round(duration_seconds, 1),
            'max_seconds': config.MAX_AUDIO_DURATION_SECONDS,
        })

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


async def transcribe_audio(
    media_base64: str,
    language: str | None = None,
    prompt: str | None = None,
) -> str:
    """
    Transcribe audio file to text using a transcription model.

    :param media_base64: Base64 string of the audio file.
    :param language: Optional language code of the audio. When None, the
        transcription model auto-detects the spoken language.
    :param prompt: Optional context prompt to guide the transcription model.

    :raises BackendError: If the audio is invalid, too large, unsupported,
        or transcription fails.

    :return: Transcribed text.
    """
    # get decoded audio and extension
    audio_bytes = await asyncio.to_thread(decode_audio, media_base64)
    ext = get_audio_format(audio_bytes)

    # validate audio format
    await _validate_audio_duration(audio_bytes, ext)

    # prepare audio file for transcription
    audio_file = BytesIO(audio_bytes)
    audio_file.name = f'audio.{ext}'

    # get the transcription model from config
    model = config.TRANSCRIBE_MODEL

    # call transcription API
    try:
        logger.info(
            f'Calling transcription API. Model: {model}, '
            f'Language: {language or "auto"}, Format: {ext}'
        )

        # call the transcription model
        response = await TRANSCRIBE_LLM.audio.transcriptions.create(
            model=model,
            file=audio_file,
            response_format='json',
            prompt=prompt or omit,
            language=language or omit,
        )

        # log success and return
        logger.info(
            f'Transcription successful. Text length: {len(response.text)} chars'
        )
        return response.text

    # error during transcription: log and raise
    except Exception as e:
        logger.error(
            f'Transcription API call failed. Model: {model}, Error: {str(e)}'
        )
        raise TranscriptionError() from e
