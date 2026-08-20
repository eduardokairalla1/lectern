"""
Client request metadata helpers.
"""

# --- IMPORTS ---
from fastapi import Request


# --- CODE ---
def get_client_ip(request: Request) -> str | None:
    """
    Extracts the client IP address from the request headers.

    :param request: FastAPI request object.

    :return: The resolved client IP, or None if unavailable.
    """
    # get the client IP from the cloudflare connecting IP header
    cf_ip = request.headers.get('cf-connecting-ip')

    # client IP is present in the headers: return it
    if cf_ip:
        return cf_ip

    # get the client IP from the x-forwarded-for header
    forwarded = request.headers.get('x-forwarded-for')

    # client IP is present in the headers: return it
    if forwarded:
        return forwarded.split(',')[0].strip()

    # no headers are present: return the client IP from the request object
    return request.client.host if request.client else None
