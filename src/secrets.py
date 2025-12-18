import httpx


def fetch_vault_secret(*, addr: str, token: str, mount: str, path: str) -> dict[str, str]:
    url = f"{addr.rstrip('/')}/v1/{mount}/data/{path.lstrip('/')}"
    headers = {"X-Vault-Token": token}
    with httpx.Client(timeout=5.0) as client:
        resp = client.get(url, headers=headers)
        resp.raise_for_status()
        payload = resp.json()
    return payload.get("data", {}).get("data", {}) or {}
