"""GitHub client: strip credentials on redirects to artifact hosts."""
import json
import os
import urllib.parse
import urllib.request

class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, new_url):
        result = super().redirect_request(request, fp, code, msg, headers, new_url)
        if result and urllib.parse.urlsplit(request.full_url).netloc != urllib.parse.urlsplit(new_url).netloc:
            result.remove_header('Authorization')
        return result

def request(url, data=None, method=None):
    headers = {'Authorization': 'Bearer ' + os.environ['GH_TOKEN'],
               'User-Agent': 'deeler-maintenance', 'Accept': 'application/vnd.github+json',
               'Content-Type': 'application/json'}
    body = None if data is None else json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.build_opener(SafeRedirect()).open(req, timeout=45) as response:
        return response.read()
