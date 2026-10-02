"""Provision the existing owner identity without exposing it to public sign-up.

WORKER_URL and STATE_TOKEN come from the operator's trusted environment.
Existing owners need no migration. Password input is never echoed or printed.
"""
import getpass
import json
import os
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def main():
    email = input("Owner email: ").strip()
    password = getpass.getpass("Owner password (at least 10 characters): ")
    if password != getpass.getpass("Repeat password: "):
        raise SystemExit("Passwords differ")
    request = Request(os.environ["WORKER_URL"].rstrip("/") + "/api/auth/bootstrap",
                      data=json.dumps({"email": email, "password": password}).encode(),
                      headers={"content-type": "application/json",
                               "x-state-token": os.environ["STATE_TOKEN"]})
    try:
        with urlopen(request, timeout=30) as response:
            if json.load(response).get("scope") != "owner":
                raise SystemExit("Owner was not provisioned")
    except HTTPError as error:
        raise SystemExit(f"Provisioning failed (HTTP {error.code}); existing owners need no migration") from None
    print("Owner provisioned. Sign in through Profiil with the same credentials.")


if __name__ == "__main__":
    main()
