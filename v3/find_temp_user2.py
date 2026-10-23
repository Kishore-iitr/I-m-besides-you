import urllib.request

url = 'https://gui-cdn.puter.com/bundle.min.js'
b_txt = urllib.request.urlopen(url).read().decode('utf-8')
idx = 3243742
print(b_txt[idx-500:idx+500])
