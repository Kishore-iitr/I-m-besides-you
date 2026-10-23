import urllib.request

url = 'https://gui-cdn.puter.com/bundle.min.js'
b_txt = urllib.request.urlopen(url).read().decode('utf-8')
idx = b_txt.find('getUserAppToken')
print('Index:', idx)
if idx != -1:
    print(b_txt[idx-100:idx+400])
