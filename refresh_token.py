import base64
import os
import sys

import requests
from nacl import encoding, public


def refresh_instagram_token(access_token: str) -> str:
    """Instagram トークンを延長して新しいトークンを返す（有効期限 +60日）。"""
    url = "https://graph.instagram.com/refresh_access_token"
    params = {
        "grant_type": "ig_refresh_token",
        "access_token": access_token,
    }
    resp = requests.get(url, params=params)
    if not resp.ok:
        print(f"[ERROR] トークン更新失敗 HTTP {resp.status_code}: {resp.text}", file=sys.stderr)
        resp.raise_for_status()
    data = resp.json()
    expires_days = data.get("expires_in", 0) // 86400
    print(f"Instagram トークン更新成功（有効期限: あと {expires_days} 日）")
    return data["access_token"]


def encrypt_secret(public_key_b64: str, secret_value: str) -> str:
    """GitHub API が要求する libsodium SealedBox 暗号化。"""
    key_bytes = base64.b64decode(public_key_b64)
    pub_key = public.PublicKey(key_bytes)
    sealed = public.SealedBox(pub_key)
    encrypted = sealed.encrypt(secret_value.encode("utf-8"))
    return base64.b64encode(encrypted).decode("utf-8")


def update_github_secret(repo: str, secret_name: str, secret_value: str, gh_pat: str) -> None:
    """GitHub Actions シークレットを上書き更新する。"""
    headers = {
        "Authorization": f"Bearer {gh_pat}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    # リポジトリの公開鍵を取得（暗号化に必要）
    pk_url = f"https://api.github.com/repos/{repo}/actions/secrets/public-key"
    pk_resp = requests.get(pk_url, headers=headers)
    if not pk_resp.ok:
        print(f"[ERROR] 公開鍵取得失敗 HTTP {pk_resp.status_code}: {pk_resp.text}", file=sys.stderr)
        pk_resp.raise_for_status()
    pk_data = pk_resp.json()

    # シークレットを暗号化して PUT
    encrypted_value = encrypt_secret(pk_data["key"], secret_value)
    secret_url = f"https://api.github.com/repos/{repo}/actions/secrets/{secret_name}"
    put_resp = requests.put(
        secret_url,
        headers=headers,
        json={"encrypted_value": encrypted_value, "key_id": pk_data["key_id"]},
    )
    if not put_resp.ok:
        print(f"[ERROR] シークレット更新失敗 HTTP {put_resp.status_code}: {put_resp.text}", file=sys.stderr)
        put_resp.raise_for_status()
    print(f"GitHub シークレット '{secret_name}' を更新しました")


if __name__ == "__main__":
    access_token = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
    gh_pat = os.environ.get("GH_PAT", "")
    repo = os.environ.get("GITHUB_REPOSITORY", "")

    missing = [name for name, val in [
        ("INSTAGRAM_ACCESS_TOKEN", access_token),
        ("GH_PAT", gh_pat),
        ("GITHUB_REPOSITORY", repo),
    ] if not val]
    if missing:
        print(f"[ERROR] 必須の環境変数が未設定: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)

    new_token = refresh_instagram_token(access_token)
    update_github_secret(repo, "INSTAGRAM_ACCESS_TOKEN", new_token, gh_pat)
