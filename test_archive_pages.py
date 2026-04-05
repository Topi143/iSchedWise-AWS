import requests, re
s = requests.Session()
login_page = s.get('http://127.0.0.1:5000/login')
m = re.search(r'name="csrf_token"\s+value="([^"]+)"', login_page.text)
token = m.group(1) if m else ''
r = s.post('http://127.0.0.1:5000/login', data={'email': 'admin@ischedwise.com', 'password': 'admin123', 'csrf_token': token}, allow_redirects=False)
print(f'Login: {r.status_code}')
pages = ['/archive/', '/archive/schedules', '/archive/curriculum', '/archive/programs', '/archive/faculty-members', '/archive/buildings-page']
for p in pages:
    resp = s.get('http://127.0.0.1:5000' + p)
    print(f'{p}: {resp.status_code}')
