import requests
from rest_framework import status

from config.settings import env


class CallProService:
    @staticmethod
    def send(to, text):
        data = {
            "key": env("CALL_PRO_KEY"),
            "from": env("CALL_PRO_FROM"),
            "to": to,
            "text": text,
        }

        try:
            response = requests.post(env("CALL_PRO_URL"), json=data, timeout=30)

            if response.status_code != status.HTTP_200_OK:
                return None, response.text

            return None, None
        except Exception as e:
            return None, str(e)
