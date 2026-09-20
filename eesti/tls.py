"""HTTPS that verifies the same way on every machine this runs on.

Every outbound call in this project goes through `urllib`, which verifies the
server against the platform's trust store. That store is not the same on a
python.org build on macOS, in the Cloud Run image and in GitHub Actions: EKI's
archive (`arhiiv.eki.ee`, the source of EKK's rection table and of the spoken
word forms) failed with CERTIFICATE_VERIFY_FAILED on the owner's Mac while
serving the same page to the deployment. A source that cannot be verified looks
exactly like a source that is down, so the rection topic simply refused to
generate and nothing said why.

Installing certifi's bundle — the same one `requests` uses — as the default
context makes verification depend on the project's own dependencies rather than
on how Python was installed. Verification is never turned off.
"""

from __future__ import annotations

import ssl


def context() -> ssl.SSLContext:
    """A verifying context built from certifi's bundle, else the platform's."""
    try:
        import certifi
    except ImportError:  # certifi is a dependency; a stripped install still runs
        return ssl.create_default_context()
    return ssl.create_default_context(cafile=certifi.where())


def install() -> None:
    """Make `context()` the default for every `urllib` HTTPS call in-process."""
    ssl._create_default_https_context = context  # noqa: SLF001 - the documented hook
