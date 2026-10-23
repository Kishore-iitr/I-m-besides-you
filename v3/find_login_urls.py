import urllib.request
import re

b_txt = urllib.request.urlopen('https://gui-cdn.puter.com/bundle.min.js').read().decode('utf-8')
for m in re.finditer(r'url:\s*[`\'"][^`\'"]*/login[^`\'"]*[`\'"]', b_txt):
    print(m.group(0))
