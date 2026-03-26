import requests
import json
try:
    print('Testing User API...')
    u = requests.get('https://www.tikwm.com/api/user/info?unique_id=tiktok', timeout=5)
    print(u.text[:500])
except Exception as e:
    print('User Error:', e)

try:
    print('Testing Video API...')
    v = requests.get('https://www.tikwm.com/api/?url=https://www.tiktok.com/@tiktok/video/7186175510639906050', timeout=5)
    print(v.text[:500])
except Exception as e:
    print('Video Error:', e)
