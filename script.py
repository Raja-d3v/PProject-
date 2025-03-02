import requests
import json
import time
import os

# Configuration
CLIENT_ID = "AKIAT4GVSAXXI2PN6X5C"
KEY = "cnIm9HvtY5kqOQuh19Ae38H/jX7oDr1RN1GYBZ59"

# Token endpoints and scopes
TOKEN_ENDPOINT = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
DEVICE_CODE_ENDPOINT = "https://login.microsoftonline.com/common/oauth2/v2.0/devicecode"
GRAPH_SCOPE = "https://graph.microsoft.com/.default"
AZURE_SCOPE = "https://management.azure.com/.default"

# File to store refresh token
TOKEN_FILE = "refresh_token.txt"

def get_device_code():
    """Request a device code for initial authorization."""
    payload = {
        "client_id": CLIENT_ID,
        "scope": f"{GRAPH_SCOPE} {AZURE_SCOPE} offline_access"
    }
    response = requests.post(DEVICE_CODE_ENDPOINT, data=payload)
    if response.status_code == 200:
        data = response.json()
        print(f"Go to: {data['verification_uri']}")
        print(f"Enter code: {data['user_code']}")
        return data["device_code"], data["interval"]
    else:
        raise Exception("Failed to get device code: " + response.text)

def poll_for_token(device_code, interval):
    """Poll for access and refresh tokens after user consent."""
    payload = {
        "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        "client_id": CLIENT_ID,
        "device_code": device_code
    }
    while True:
        response = requests.post(TOKEN_ENDPOINT, data=payload)
        if response.status_code == 200:
            data = response.json()
            return data["access_token"], data["refresh_token"], data["expires_in"]
        elif "authorization_pending" in response.text:
            time.sleep(interval)
        else:
            raise Exception("Error polling token: " + response.text)

def refresh_access_token(refresh_token):
    """Refresh the access token using the refresh token."""
    payload = {
        "grant_type": "refresh_token",
        "client_id": CLIENT_ID,
        "refresh_token": refresh_token,
        "scope": f"{GRAPH_SCOPE} {AZURE_SCOPE}"
    }
    response = requests.post(TOKEN_ENDPOINT, data=payload)
    if response.status_code == 200:
        data = response.json()
        return data["access_token"], data["refresh_token"], data["expires_in"]
    else:
        raise Exception("Error refreshing token: " + response.text)

def save_refresh_token(refresh_token):
    """Save the refresh token to a file."""
    with open(TOKEN_FILE, "w") as f:
        f.write(refresh_token)

def load_refresh_token():
    """Load the refresh token from a file, or use KEY if no file exists."""
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r") as f:
            return f.read().strip()
    return KEY  # Use KEY as the initial refresh token if no file exists

def send_teams_message(access_token, team_id, channel_id, message):
    """Send a message to a Teams channel."""
    url = f"https://graph.microsoft.com/v1.0/teams/{team_id}/channels/{channel_id}/messages"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "body": {
            "content": message,
            "contentType": "text"
        }
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 201:
        print(f"Sent Teams message: {message}")
    else:
        print(f"Error sending message: {response.status_code} - {response.text}")

def update_presence(access_token, status="Available"):
    """Update user presence status in Teams."""
    url = "https://graph.microsoft.com/v1.0/me/presence/setPresence"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "sessionId": "lazy-script-session",
        "availability": status,
        "activity": "Available" if status == "Available" else "Busy"
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        print(f"Updated presence to {status}")
    else:
        print(f"Error updating presence: {response.status_code} - {response.text}")

def list_azure_resource_groups(access_token, subscription_id):
    """List Azure resource groups to simulate activity."""
    url = f"https://management.azure.com/subscriptions/{subscription_id}/resourceGroups?api-version=2021-04-01"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        groups = response.json()["value"]
        print(f"Listed {len(groups)} resource groups")
    else:
        print(f"Error listing resource groups: {response.status_code} - {response.text}")

def initialize_tokens():
    """Initialize or load tokens."""
    refresh_token = load_refresh_token()
    if not refresh_token:
        print("No refresh token found. Starting device code flow...")
        device_code, interval = get_device_code()
        access_token, refresh_token, expires_in = poll_for_token(device_code, interval)
        save_refresh_token(refresh_token)
        print("Refresh token saved.")
    else:
        try:
            access_token, refresh_token, expires_in = refresh_access_token(refresh_token)
            save_refresh_token(refresh_token)
        except Exception as e:
            print(f"Refresh token invalid: {e}. Starting device code flow...")
            device_code, interval = get_device_code()
            access_token, refresh_token, expires_in = poll_for_token(device_code, interval)
            save_refresh_token(refresh_token)
            print("New refresh token saved.")
    return access_token, refresh_token, expires_in

def main():
    """Main loop to simulate activity."""
    access_token, refresh_token, expires_in = initialize_tokens()
    last_refresh = time.time()

    while True:
        current_time = time.time()
        # Refresh token if nearing expiration (within 5 minutes)
        if current_time - last_refresh >= expires_in - 300:
            try:
                access_token, refresh_token, expires_in = refresh_access_token(refresh_token)
                save_refresh_token(refresh_token)
                last_refresh = current_time
                print("Access token refreshed.")
            except Exception as e:
                print(f"Token refresh failed: {e}. Re-running initialization...")
                access_token, refresh_token, expires_in = initialize_tokens()
                last_refresh = time.time()

        # Simulate activities
        send_teams_message(access_token, TEAM_ID, CHANNEL_ID, "I'm working on something...")
        update_presence(access_token, "Busy")
        list_azure_resource_groups(access_token, SUBSCRIPTION_ID)

        # Wait 1 hour before next activity
        time.sleep(3600)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Script failed: {e}")
