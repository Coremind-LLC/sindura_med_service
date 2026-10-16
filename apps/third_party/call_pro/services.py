import logging

import requests
from rest_framework import status

from config.settings import env

logger = logging.getLogger(__name__)


class CallProService:
    @staticmethod
    def send(to, text) -> tuple[None, str | None]:
        try:
            response = requests.get(
                env("CALL_PRO_URL"),
                params={
                    "key": env("CALL_PRO_KEY"),
                    "from": env("CALL_PRO_FROM"),
                    "to": to,
                    "text": text,
                },
                timeout=30,
            )

            if response.status_code != status.HTTP_200_OK:
                return None, response.text

            return None, None
        except Exception as e:
            logger.exception("Failed to send CallPro SMS")
            return None, str(e)
