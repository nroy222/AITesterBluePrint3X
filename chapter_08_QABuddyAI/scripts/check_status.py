import urllib.request, json

r = urllib.request.urlopen('http://127.0.0.1:5080/api/stats', timeout=10)
d = json.loads(r.read())
print('Total points:', d['total'])
for k, v in d['by_source'].items():
    if v > 0:
        print(f'  {k}: {v}')