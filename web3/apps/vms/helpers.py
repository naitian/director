import requests
import json
import os

from django.conf import settings

from raven.contrib.django.raven_compat.models import client


def call_api(action=None, **kwargs):
    agent_path = "https://deneb.agent.lxc.deneb.csl.tjhsst.edu/"
    cert_path = os.path.join(settings.PROJECT_ROOT, "settings/conductor.pem")
    resp = requests.request(method=("POST" if action else "GET"), json={"method": action, "args": kwargs}, url=agent_path, cert=cert_path, verify=False)
    if resp.status_code == 500:
        if settings.DEBUG:
            print("{} {}\n{} {}".format(resp.status_code, resp.text, action, kwargs))
        else:
            client.captureMessage("Conductor API Request Failure: {} {}\n{} {}\n".format(resp.status_code, resp.text, action, kwargs))
        return None
    return json.loads(resp.text)
