import urllib.request
import json

API_KEY = "super-secret"


def radio_essen_current() -> str:
    url = "https://api-prod.nrwlokalradios.com/playlist/current?station=12"
    headers = {'X-Auth': API_KEY}
    req = urllib.request.Request(url, headers=headers)

    with urllib.request.urlopen(req) as res:
        data = json.loads(res.read().decode())
        return f"{data['artist']}: {data['title']}"


def euro() -> str:
    return "€"


globals = {
    "radio_essen_current": radio_essen_current,
    "euro": euro,
    "name": "Mike Barkmin"
}
