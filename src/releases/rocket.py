import requests

from django.conf import settings


class RocketClient:

    @classmethod
    def is_configured_properly(cls) -> bool:
        return bool(settings.ROCKET_HOOK_URL)

    def send_message(self, message: str, color: str = 'black'):
        if self.is_configured_properly():
            response = requests.post(
                settings.ROCKET_HOOK_URL,
                json={
                    "text": "",
                    "attachments": [{
                        "author_name": "Release Manager",
                        "color": color,
                        "thumb_url": None,
                        "text": message,
                    }]
                }
            )
            response.raise_for_status()
