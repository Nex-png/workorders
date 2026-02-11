import os
from twilio.rest import Client

_sid = os.getenv("TWILIO_ACCOUNT_SID")
_token = os.getenv("TWILIO_AUTH_TOKEN")
_from = os.getenv("TWILIO_FROM_NUMBER")
_to = os.getenv("ALERT_TO_NUMBER")

_client = Client(_sid, _token)


def send_sms(message: str):
    if not all([_sid, _token, _from, _to]):
        return  # silently skip if not configured

    _client.messages.create(
        body=message,
        from_=_from,
        to=_to,
    )
