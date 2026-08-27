import urllib.request, json
req = urllib.request.Request(
    'https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key=AQ.Ab8RN6LC-F4au_yHIBbTOhDHaH8NbJZu4XzYOtXYyTh_nMx1-Q',
    data=b'{"contents":[{"parts":[{"text":"test"}]}],"generationConfig":{"responseMimeType":"application/json"}}',
    headers={'Content-Type': 'application/json'}
)
try:
    print(urllib.request.urlopen(req, timeout=5).read().decode())
except Exception as e:
    print("ERROR:", e)
