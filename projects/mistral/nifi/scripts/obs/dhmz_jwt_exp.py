"""Extract the 'exp' claim from a JWT token read from STDIN.

Outputs the epoch-second expiry value as plain text to STDOUT.
Used by the NiFi "Ensure valid DHMZ token" Process Group to store
the token expiry in the distributed cache.

Exit codes:
    0  success
    1  invalid or missing token
"""

import base64
import json
import sys


def main():
    raw = sys.stdin.buffer.read().decode("utf-8").strip()
    if not raw:
        print("empty input", file=sys.stderr)
        return 1

    parts = raw.split(".")
    if len(parts) != 3:
        print(f"not a JWT (got {len(parts)} parts)", file=sys.stderr)
        return 1

    # base64url -> base64
    payload_b64 = parts[1].replace("-", "+").replace("_", "/")
    # add padding
    padding = 4 - len(payload_b64) % 4
    if padding != 4:
        payload_b64 += "=" * padding

    try:
        payload_json = base64.b64decode(payload_b64)
        payload = json.loads(payload_json)
    except Exception as exc:
        print(f"cannot decode JWT payload: {exc}", file=sys.stderr)
        return 1

    exp = payload.get("exp")
    if exp is None:
        print("JWT payload has no 'exp' claim", file=sys.stderr)
        return 1

    sys.stdout.write(str(int(exp)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
