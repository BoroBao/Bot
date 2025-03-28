import requests

DROPBOX_APP_KEY = "2v29gcbr3288tk1"
DROPBOX_APP_SECRET = "yrqnf5lx9eg2adk"
DROPBOX_REFRESH_TOKEN = "gK9jaGJGfhwAAAAAAAAAAcuT3DFFKixUDWwhsjiHvosOWZDeR3A-6tqgmoc-Zd9P"

def get_dropbox_access_token():
    """
    Refreshes the Dropbox access token using the refresh token.
    """
    url = "https://api.dropboxapi.com/oauth2/token"
    data = {
        "grant_type": "refresh_token",
        "refresh_token": DROPBOX_REFRESH_TOKEN,
        "client_id": DROPBOX_APP_KEY,
        "client_secret": DROPBOX_APP_SECRET
    }

    print("🔍 Payload gửi đi:", data)  # Debug payload

    try:
        response = requests.post(url, data=data)
        print("🔍 Response status code:", response.status_code)  # Debug status
        print("🔍 Response text:", response.text)  # Debug response body
        response.raise_for_status()
        new_token = response.json().get("access_token")
        if new_token:
            print("✅ Dropbox access token refreshed successfully.")
            return new_token
        else:
            print("❌ Failed to refresh Dropbox token.")
            return None
    except requests.exceptions.RequestException as e:
        print(f"❌ Error refreshing Dropbox token: {e}")
        return None

# Test làm mới token
if __name__ == "__main__":
    access_token = get_dropbox_access_token()
    if access_token:
        print("New Access Token:", access_token)
