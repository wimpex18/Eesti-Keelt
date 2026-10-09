"""Open only this Worker's hostname after its public-safe origin is deployed.

Run by deploy.yml. Requires Account Access: Apps and Policies Write on the
Cloudflare deployment token. Other applications and wildcard domains remain
untouched. Failure leaves deployment visibly incomplete, ready to retry.
"""
from __future__ import annotations

import json
import os
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

API = "https://api.cloudflare.com/client/v4"
USER_AGENT = "Grove-deploy/1.0"


def request_json(url, *, headers=None, method="GET"):
    headers = {"User-Agent": USER_AGENT, **(headers or {})}
    with urlopen(Request(url, headers=headers, method=method), timeout=30) as response:
        return json.load(response)


def _host(value):
    """The hostname of an Access domain or destination ("host", "host/*", URI)."""
    value = (value or "").strip()
    return (urlsplit(value).hostname if "://" in value else value.split("/", 1)[0]).lower()


def app_hosts(app):
    """Every hostname an Access application covers, in old and new API shapes."""
    hosts = {_host(app.get("domain"))} | {_host(d) for d in app.get("self_hosted_domains") or []}
    hosts |= {_host(d.get("uri")) for d in app.get("destinations") or []
              if isinstance(d, dict) and d.get("type", "public") == "public"}
    return hosts - {""}


def matching_apps(apps, hostname):
    return [app for app in apps if hostname in app_hosts(app)]


def open_public(env):
    url = urlsplit(env["WORKER_URL"])
    hostname = url.hostname
    if url.scheme != "https" or not hostname or not hostname.endswith(".workers.dev") or url.path not in ("", "/") or url.query or url.fragment or url.username:
        raise RuntimeError("WORKER_URL must be this Worker's workers.dev HTTPS URL")
    # Cloud Build and the Worker deploy independently. Do not expose old origin
    # code: it served personal corpus items without checking account scope.
    origin_headers = {"x-proxy-token": env["PROXY_TOKEN"], "x-eesti-scope": "guest"}
    for attempt in range(100):
        try:
            health = request_json(env["CLOUD_RUN_URL"].rstrip("/") + "/api/health",
                                  headers=origin_headers)
            if health.get("public_access") is True and health.get("origin_guarded") is True:
                break
        except (HTTPError, URLError, TimeoutError):
            pass
        if attempt == 99:
            raise RuntimeError("Public-safe origin has not deployed; retry after Cloud Build completes")
        if attempt % 4 == 0:
            print("Waiting for the public-safe Cloud Run build…", flush=True)
        time.sleep(15)
    def access_json(url, **kwargs):
        try:
            return request_json(url, **kwargs)
        except HTTPError as error:
            raise RuntimeError(f"Access-app API returned HTTP {error.code}; check token Account Access: Apps and Policies Write permission") from None

    headers = {"Authorization": "Bearer " + env["CLOUDFLARE_API_TOKEN"]}
    endpoint = API + "/accounts/" + env["CLOUDFLARE_ACCOUNT_ID"] + "/access/apps"
    apps = []
    page = 1
    while True:
        result = access_json(endpoint + f"?page={page}&per_page=50", headers=headers)
        if result.get("success") is not True:
            raise RuntimeError("Cannot list access applications; check token permissions")
        apps.extend(result["result"])
        if page >= result.get("result_info", {}).get("total_pages", 1):
            break
        page += 1
    for app in matching_apps(apps, hostname):
        if app_hosts(app) != {hostname}:
            raise RuntimeError("Hostname shares an access application with other domains; split it before retrying")
        result = access_json(endpoint + "/" + app["id"], headers=headers, method="DELETE")
        if result.get("success") is not True:
            raise RuntimeError("Cannot open this hostname; token needs Access Apps and Policies Write")
        print("Removed the login gate for " + hostname, flush=True)
    # An HTTP 200 login page is not enough: verify the Worker's own anonymous
    # identity response as well as its shell and health.
    public = env["WORKER_URL"].rstrip("/")
    try:
        me = request_json(public + "/api/auth/me")
    except (HTTPError, ValueError):
        # A login page (a redirect to cloudflareaccess.com) instead of JSON.
        raise RuntimeError(
            f"{hostname} is still behind a login gate. Remove the Cloudflare Access "
            "application or the Worker's workers.dev Access setting that covers it "
            "(wildcard and shared applications are left for the owner), then rerun "
            "the deploy workflow") from None
    if me.get("scope") != "guest":
        raise RuntimeError("Anonymous identity must be guest")
    health = request_json(public + "/api/health")
    if not health.get("public_access"):
        raise RuntimeError("Public URL is not serving the public-safe origin")
    with urlopen(Request(public + "/", headers={"User-Agent": USER_AGENT}), timeout=30) as response:
        if response.status != 200 or b"Grove" not in response.read():
            raise RuntimeError("Public shell is not serving Grove")
    print("Public shell, health and anonymous guest identity verified", flush=True)


if __name__ == "__main__":
    try:
        open_public(os.environ)
    except (KeyError, RuntimeError, HTTPError, URLError, TimeoutError, ValueError) as error:
        # Do not print request objects or credential headers.
        print("Public access deployment failed: " + (str(error) if isinstance(error, RuntimeError)
                                                     else type(error).__name__), flush=True)
        raise SystemExit(1)
