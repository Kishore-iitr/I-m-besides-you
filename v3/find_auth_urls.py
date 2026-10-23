import urllib.request
import re

b_txt = urllib.request.urlopen('https://gui-cdn.puter.com/bundle.min.js').read().decode('utf-8')
matches = set(re.findall(r'"/(?:login|signup|user|auth|register|account)/[a-zA-Z0-9_\-]+"', b_txt))
for m in sorted(matches):
    print(m)
