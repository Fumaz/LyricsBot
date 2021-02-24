import requests


def from_url(url) -> str:
    if '.com/raw/' not in url:
        url = url.split('.com/')
        url = url[0] + '.com/raw/' + url[1]

    request = requests.get(url)
    return request.text
