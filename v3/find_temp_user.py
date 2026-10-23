import urllib.request
import re

url = 'https://gui-cdn.puter.com/bundle.min.js'
b_txt = urllib.request.urlopen(url).read().decode('utf-8')
idx = b_txt.find('attempt_temp_user_creation')
print('Index:', idx)
if idx != -1:
    print('Snippet around attempt_temp_user_creation:')
    print(b_txt[max(0, idx-100):idx+400])
