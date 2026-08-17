from __future__ import annotations

import os
import smtplib
from email.mime.text import MIMEText


class NotificationService:
    """
    Sends email notifications via SMTP.

    Credentials are NEVER hardcoded or committed -- they come from
    Streamlit secrets (.streamlit/secrets.toml, read via st.secrets) when
    available, falling back to environment variables. The env var
    fallback also makes this usable outside of a running Streamlit app
    (e.g. from scripts/run_watchlist_scan.py invoked by cron), where
    st.secrets has nothing to read from.

    Expected keys (in either secrets.toml or the environment):
        SMTP_HOST     (default: "smtp.gmail.com")
        SMTP_PORT     (default: "587")
        SMTP_USERNAME (required -- also used as the "From" address)
        SMTP_PASSWORD (required -- an app password, not a login password,
                       for providers like Gmail that require one)
    """

    def __init__(self) -> None:
        self._smtp_host = self._get_config("SMTP_HOST") or "smtp.gmail.com"
        self._smtp_port = int(self._get_config("SMTP_PORT") or "587")
        self._smtp_username = self._get_config("SMTP_USERNAME")
        self._smtp_password = self._get_config("SMTP_PASSWORD")

    def send_email(self, to: str, subject: str, body: str) -> bool:
        """
        Send a plain-text email.

        Args:
            to: Recipient address.
            subject: Email subject line.
            body: Plain-text email body.

        Returns:
            True if the SMTP server accepted the message.

        Raises:
            RuntimeError: If SMTP_USERNAME/SMTP_PASSWORD aren't configured.
            smtplib.SMTPException: On any SMTP-level failure (auth
                rejected, connection refused, etc.) -- callers that scan
                many tickers should catch this per-alert so one bad send
                doesn't abort the rest of the batch (see
                scripts/run_watchlist_scan.py).
        """
        if not self._smtp_username or not self._smtp_password:
            raise RuntimeError(
                "SMTP credentials not configured. Set SMTP_USERNAME and "
                "SMTP_PASSWORD via .streamlit/secrets.toml or environment "
                "variables."
            )

        message = MIMEText(body)
        message["Subject"] = subject
        message["From"] = self._smtp_username
        message["To"] = to

        with smtplib.SMTP(self._smtp_host, self._smtp_port, timeout=10) as server:
            server.starttls()
            server.login(self._smtp_username, self._smtp_password)
            server.sendmail(self._smtp_username, [to], message.as_string())

        return True

    @staticmethod
    def _get_config(key: str) -> str | None:
        """
        Look up a config value from Streamlit secrets first, then the
        environment. Never hardcoded, never logged.
        """
        try:
            import streamlit as st

            if key in st.secrets:
                return str(st.secrets[key])
        except Exception:
            # No Streamlit runtime, no secrets.toml, or the key isn't
            # there -- fall through to the environment variable.
            pass

        return os.environ.get(key)
