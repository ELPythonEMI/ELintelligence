from __future__ import annotations

from .paths import is_portable

SERVICE = "ELintelligence"
ACCOUNT = "brave-search-api-key"


class SecretStore:
    def __init__(self) -> None:
        self._fallback = ""

    def load_brave_key(self) -> str:
        if is_portable():
            # In portable mode the key stays only in RAM so nothing secret is left on the PC or USB.
            return self._fallback
        try:
            import keyring
            return keyring.get_password(SERVICE, ACCOUNT) or ""
        except Exception:
            return self._fallback

    def save_brave_key(self, value: str) -> None:
        value = value.strip()
        self._fallback = value
        if is_portable():
            return
        try:
            import keyring
            if value:
                keyring.set_password(SERVICE, ACCOUNT, value)
            else:
                try:
                    keyring.delete_password(SERVICE, ACCOUNT)
                except Exception:
                    pass
        except Exception:
            pass
