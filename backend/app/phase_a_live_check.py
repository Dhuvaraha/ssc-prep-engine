"""LIVE-01: exactly one operator-approved anonymous request, no body export.

Do not run against production before release review. A denial is bounded
evidence for one route only; this tool never declares production safe.
"""
import argparse
import json
from pathlib import Path
from urllib.parse import urlparse

import httpx


def summarize(status, headers, payload, private_ids, expected_sha):
    examples = payload.get("solved_examples", []) if isinstance(payload, dict) else []
    sensitive = {"correct_option", "explanation", "fast_method", "source_reference", "source_notes"}
    def has_sensitive(value):
        if isinstance(value, dict):
            return any(key in sensitive and val not in (None, "", []) or has_sensitive(val) for key, val in value.items())
        if isinstance(value, list):
            return any(has_sensitive(item) for item in value)
        return False
    return {"status": status, "cache_control":headers.get("cache-control", ""),
            "solved_example_count":len(examples), "sensitive_fields_present":has_sensitive(payload),
            "private_id_match":any(isinstance(item,dict) and item.get("id") in private_ids for item in examples),
            "release_sha_matches":headers.get("x-ssc-release") == expected_sha,
            "scope":"one anonymous package request only; not production safety sign-off"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--expected-sha", required=True)
    parser.add_argument("--private-id-manifest", type=Path, required=True)
    parser.add_argument("--operator-approved", action="store_true")
    args = parser.parse_args()
    url = urlparse(args.url)
    if not args.operator_approved or url.scheme != "https" or url.username or url.password or url.query or not url.path.endswith("/package"):
        parser.error("Explicit operator approval and exact HTTPS package URL without credentials/query required")
    private_ids = set(json.loads(args.private_id_manifest.read_text(encoding="utf-8")))
    try:
        with httpx.Client(timeout=15, follow_redirects=False, trust_env=False) as client:
            with client.stream("GET", args.url, headers={"Cache-Control":"no-store"}) as response:
                body = bytearray()
                for chunk in response.iter_bytes():
                    body.extend(chunk)
                    if len(body) > 1_048_576:
                        print(json.dumps({"status":response.status_code, "bounded_read_exceeded":True}))
                        return
                try:
                    payload = json.loads(body)
                except (ValueError, UnicodeError):
                    payload = None
                print(json.dumps(summarize(response.status_code,response.headers,payload,private_ids,args.expected_sha),sort_keys=True))
    except httpx.HTTPError:
        # Exception strings can contain URLs. Export no bodies, IDs or locators.
        print(json.dumps({"network_error":True,"scope":"no live safety conclusion"}))


if __name__ == "__main__":
    main()
