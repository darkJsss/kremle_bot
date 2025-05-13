import requests
from base64 import b64encode

response = requests.get('http://127.0.0.1:5000/api/leaderboard')
print(response.json())
auth_header = {
    'Authorization': 'Basic ' + b64encode(b'Damir1:123456').decode('utf-8')
}
response = requests.get('http://127.0.0.1:5000/api/user/stats', headers=auth_header)
print(response.json())
