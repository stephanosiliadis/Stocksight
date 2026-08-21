from __future__ import annotations

import sys


class NotificationService:
    """
    Sends local desktop notifications using plyer.
    """

    def send_notification(self, title: str, message: str) -> bool:
        """
        Send a native desktop notification.

        Args:
            title: Title for the desktop notification window.
            message: Body text for the notification.

        Returns:
            True if the notification was sent successfully.
        """
        try:
            from plyer import notification

            notification.notify(
                title=title,
                message=message,
                app_name="Stocksight",
                timeout=10,
            )
            return True
        except Exception as exc:
            print(f"Failed to display desktop notification: {exc}", file=sys.stderr)
            return False
