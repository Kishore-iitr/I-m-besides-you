import urllib.request
import re

b_txt = urllib.request.urlopen('https://gui-cdn.puter.com/bundle.min.js').read().decode('utf-8')
for m in re.finditer(r'fetch\([`\'"][^`\'"]*login', b_txt):
    idx = m.start()
    print(b_txt[idx:idx+120])
