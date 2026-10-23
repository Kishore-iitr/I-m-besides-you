import urllib.request

b_txt = urllib.request.urlopen('https://gui-cdn.puter.com/bundle.min.js').read().decode('utf-8')
idx = b_txt.find('/login`')
print(b_txt[idx-50:idx+350])
