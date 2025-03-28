import requests

APP_KEY = "2v29gcbr3288tk1"
APP_SECRET = "yrqnf5lx9eg2adk"
AUTH_CODE = "633S0tcIR14AAAAAAAAALpbFwmYOjEm3H26WUfplgvo"

url = "https://api.dropboxapi.com/oauth2/token"
data = {
    "grant_type": "authorization_code",
    "code": AUTH_CODE,
    "client_id": APP_KEY,
    "client_secret": APP_SECRET,
}

response = requests.post(url, data=data)
print(response.json())  # In kết quả ra màn hình
