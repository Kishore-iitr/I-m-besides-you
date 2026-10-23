import urllib.request
import re

url = 'https://gui-cdn.puter.com/bundle.min.js'
b_txt = urllib.request.urlopen(url).read().decode('utf-8')
for m in re.finditer(r'/auth/[a-zA-Z0-9_\-]+', b_txt):
    print(m.group(0))
