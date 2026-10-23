import urllib.request
import re

b_txt = urllib.request.urlopen('https://gui-cdn.puter.com/bundle.min.js').read().decode('utf-8')
for m in re.finditer(r'password', b_txt, re.IGNORECASE):
    idx = m.start()
    snippet = b_txt[max(0, idx-100):idx+250]
    if 'fetch' in snippet or 'http' in snippet or 'api' in snippet:
        print('--- Snippet ---')
        print(snippet)
        break
