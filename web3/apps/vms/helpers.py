import requests
import json

from django.conf import settings

from raven.contrib.django.raven_compat.models import client


def call_api(action=None, **kwargs):
    try:
        resp = requests.request(method=("POST" if action else "GET"),
                                json={"method": action, "args": kwargs},
                                url=settings.CONDUCTOR_AGENT_PATH,
                                cert=settings.CONDUCTOR_CERT_PATH,
                                verify=False,
                                timeout=10)
    except requests.exceptions.ConnectionError:
        client.captureException()
        return None
    except requests.exceptions.ReadTimeout:
        client.captureException()
        return None

    if resp.status_code == 500 or resp.status_code == 400:
        client.captureMessage("Conductor API Request Failure: {} {}\n{} {}\n".format(resp.status_code, resp.text, action, kwargs))
        return None
    return json.loads(resp.text)
