"""HTTPS verification does not depend on how Python was installed.

EKI's archive — EKK's rection table, the spoken word forms — failed to verify
on the owner's Mac while serving the same page to the deployment, and a source
that cannot be verified looks exactly like a source that is down: the rektsioon
topic refused to generate and said only "no rections stored".
"""

from __future__ import annotations

import ssl

from eesti import tls


def test_the_project_verifies_against_its_own_bundle():
    import certifi

    ctx = tls.context()
    assert ctx.verify_mode == ssl.CERT_REQUIRED
    assert ctx.check_hostname
    assert ctx.get_ca_certs(), "no certificate authorities loaded"
    assert certifi.where()


def test_importing_the_package_installs_it():
    """Every `urllib` call in the app goes through the default context."""
    import eesti  # noqa: F401  -- the import is what installs it

    assert ssl._create_default_https_context is tls.context
