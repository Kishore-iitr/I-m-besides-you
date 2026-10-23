import urllib.request
import re
import json

url = 'https://puter.com/action/sign-in?embedded_in_popup=true&msg_id=test&attempt_temp_user_creation=true'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req) as res:
        txt = res.read().decode('utf-8')
        srcs = re.findall(r'src=["\'](.*?)["\']', txt)
        print('Script srcs:', srcs)
        # Fetch the main bundle to find temp user creation API
        for s in srcs:
            if 'main' in s or 'bundle' in s or 'index' in s or 'app' in s:
                full_s = s if s.startswith('http') else f'https://puter.com{s}'
                print('Fetching bundle:', full_s)
                b_txt = urllib.request.urlopen(full_s).read().decode('utf-8')
                for m in re.finditer(r'temp_user|temporary|create-temp|temp-user', b_txt):
                    idx = m.start()
                    print('Snippet:', b_txt[max(0, idx-100):idx+200])
                    break
except Exception as e:
    print('Error:', e)
