"""Static configuration: the OAuth/feed endpoints, on-disk locations, and the
path to the bundled sdl-freerdp.

These are process-wide constants (mostly derived from the environment once, at
import time). Anything that changes per signed-in session — the user's UPN, the
last refresh error — lives on :class:`~avd_feed_connect.auth.oauth.OAuthClient`
instead, never here.
"""

import os
import shutil
import sys
import urllib.parse

# Multi-tenant by default: "organizations" lets any work/school account sign in
# and the feed returns every workspace that account is entitled to. Override
# with AVD_TENANT to pin a single tenant. The signed-in user's UPN is normally
# learned from the token (OAuthClient.set_upn_from_token); AVD_UPN can pre-fill
# the login hint (see OAuthClient).
TENANT = os.environ.get("AVD_TENANT", "organizations")
CLIENT_ID = "a85cf173-4192-42f8-81fa-777a763e6e2c"  # Microsoft Remote Desktop (public)
SCOPE = "https://www.wvd.microsoft.com/.default offline_access openid profile"
DISCOVERY = "https://rdweb.wvd.microsoft.com/api/arm/feeddiscovery"
LOGIN = f"https://login.microsoftonline.com/{TENANT}/oauth2/v2.0"
# Registered redirect for the public MS Remote Desktop client; the browser
# lands here (a blank page) with ?code=… after an interactive sign-in.
REDIRECT = "https://login.microsoftonline.com/common/oauth2/nativeclient"
# The feed service rejects unknown clients ("INCOMPATIBLE_CLIENT_VERSION /
# Client did not send any User Agent approved header"); this is exactly the
# X-MS-User-Agent the web client sends (clientType/clientVersion sdkType/sdk).
MS_USER_AGENT = "com.microsoft.rdc.html/2.0.79.2 rdhtml-sdk/2.0.4"

ACCEPT_DISCOVERY = "application/x-msts-radc-discovery+xml,text/xml"
ACCEPT_FEED = "application/x-msts-radc+xml;radc_schema_version=2.0,text/xml"

HOME = os.path.expanduser("~")

# Data dir: use XDG_DATA_HOME (set to the app's private dir inside Flatpak) so
# the token cache and generated .rdp files land in a sane, writable place both
# packaged and unpackaged.
_DATA = os.environ.get("XDG_DATA_HOME") or os.path.join(HOME, ".local", "share")
OUT = os.path.join(_DATA, "avd-feed-connect", "feed")
CACHE = os.path.join(_DATA, "avd-feed-connect", "token-cache.json")


IS_OPENBSD = sys.platform.startswith("openbsd")


def find_sdl_freerdp():
    """Locate the FreeRDP client. In the Flatpak it is on PATH at
    /app/bin/sdl-freerdp; unpackaged, fall back to the local -cam build.

    Platforms whose FreeRDP package ships without the SDL client (OpenBSD's
    is built with WITH_CLIENT_SDL=OFF) fall back to xfreerdp, which accepts
    the same /gateway:type:arm /sec:aad command line."""
    local = os.path.join(HOME, "opt", "freerdp-sdl3-cam", "bin", "sdl-freerdp")
    return (os.environ.get("AVD_SDL_FREERDP")
            or shutil.which("sdl-freerdp")
            or (local if os.path.exists(local) else None)
            or shutil.which("xfreerdp")
            or local)


def is_xfreerdp(binary):
    """True when ``binary`` is the X11 client rather than sdl-freerdp."""
    return os.path.basename(binary or "").startswith("xfreerdp")


def find_audio_backend():
    """FreeRDP audio subsystem: AVD_SOUND wins ("none" disables audio
    redirection); otherwise sndio on OpenBSD and PulseAudio elsewhere."""
    override = os.environ.get("AVD_SOUND", "").strip().lower()
    if override:
        return override
    return "sndio" if IS_OPENBSD else "pulse"


def audio_args(backend=None):
    """Playback + microphone flags for the chosen audio backend."""
    backend = backend or find_audio_backend()
    if backend == "none":
        return []
    if backend == "pulse":
        return ["/sound:sys:pulse", "/microphone"]  # unchanged Linux behaviour
    return [f"/sound:sys:{backend}", f"/microphone:sys:{backend}"]


SDL = find_sdl_freerdp()
# Only needed unpackaged (Flatpak resolves libs via rpath); empty = don't touch.
SDL_LIBS = os.environ.get("AVD_SDL_LIBS", os.path.join(HOME, "opt", "sdl3", "lib"))

AAD_LOGIN_HOST = "login.microsoftonline.com"


def is_aad_login_url(url):
    """True only for an https URL on the Entra login host. FreeRDP's "Browse to:"
    URL is loaded in a WebView that shares our SSO cookies, so nothing else
    may be loaded there."""
    try:
        p = urllib.parse.urlparse(url)
        return p.scheme == "https" and (p.hostname or "").lower() == AAD_LOGIN_HOST
    except ValueError:
        return False


# Hosts a bearer token may be sent to. Feed XML supplies the feed, .rdp and icon
# URLs, so they are checked before the Authorization header is attached.
TRUSTED_SUFFIXES = (".microsoft.com", ".microsoftonline.com")


def is_trusted_url(url):
    """True only for an https URL on a Microsoft host (dot-boundary match, so
    ``evilmicrosoft.com`` and ``microsoft.com.evil.io`` are rejected)."""
    try:
        p = urllib.parse.urlparse(url)
        host = (p.hostname or "").lower()
    except ValueError:
        return False
    return p.scheme == "https" and any(
        host == s[1:] or host.endswith(s) for s in TRUSTED_SUFFIXES)
