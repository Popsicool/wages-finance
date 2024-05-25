import requests

url = "https://api.sandbox.safehavenmfb.com/identity/v2"

payload = {
    "type": "BVN",
    "number": "22234567876",
    "debitAccountNumber": "0103351379"
}
headers = {
    "accept": "application/json",
    "content-type": "application/json",
    "Authorization": "Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJodHRwczovL2FwaS5zYW5kYm94LnNhZmVoYXZlbm1mYi5jb20iLCJzdWIiOiJlZjZlYTYzZWViNjc4MzA4YmJjMDkwNmVhY2FiOGM0YyIsImF1ZCI6Imh0dHBzOi8vd3d3LnBvcHNpY29vbC5mb2ctYWdyaWMuY29tIiwianRpIjoiY2ExNTVlNTY1OWE5MzQyYTA0YTk2MTA2OGJhYWQ0ZGYiLCJncmFudF90eXBlIjoiYWNjZXNzX3Rva2VuIiwic2NvcGVzIjpbIlJFQUQiLCJXUklURSIsIlBBWSJdLCJpYnNfY2xpZW50X2lkIjoiNjUwZDZlOWNlN2YzZTQwMDI0Y2MzNGZmIiwiaWJzX3VzZXJfaWQiOiI2NTBkNmU5ZGU3ZjNlNDAwMjRjYzM1MDgiLCJpYXQiOjE3MTY2NDA5OTMsImV4cCI6MTcxNjY0MzM5M30.ipeCx390eGY9Miq7TRgY1mbmUXTJa_xrZtwVN9MK1Dh0Yvcg7qI-IrMkAPx9HSjySZs1-_AnEFFobT3llB9k47tYJ3dQWvlINkj4kTSLMeE1yoQKh0vb6CvZYNcimC2-MwNmifwjtWRHu2JUZdPVAnaWFa5XIOA8h7RyomJorjI"
}

response = requests.post(url, json=payload, headers=headers)

print(response.text)