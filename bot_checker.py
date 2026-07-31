import os
import json
import time
import requests
from bs4 import BeautifulSoup
import urllib3
from dotenv import load_dotenv

# Disable SSL warnings due to potential local network interception
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Load configuration
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "600"))  # Default: 10 minutes

STATE_FILE = "bot_state.json"
SETNEG_SEARCH_URL = "https://www.setneg.go.id/post/hasilcari?site-search=upacara"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_state(state):
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=4)
    except Exception as e:
        print(f"Error saving state: {e}")

def send_telegram_message(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("[Skipped Telegram] Token or Chat ID not configured.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            print("Telegram notification sent successfully.")
        else:
            print(f"Failed to send Telegram message: {response.text}")
    except Exception as e:
        print(f"Error sending Telegram notification: {e}")

def check_announcements():
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Checking Kemensesneg website...")
    try:
        response = requests.get(SETNEG_SEARCH_URL, headers=HEADERS, timeout=15, verify=False)
        if response.status_code != 200:
            print(f"Error fetching Kemensesneg search page: HTTP {response.status_code}")
            return
            
        soup = BeautifulSoup(response.content, 'html.parser')
        links = soup.find_all('a', href=True)
        
        # Filter links that represent articles
        articles = {}
        for link in links:
            href = link['href']
            text = link.get_text(strip=True)
            if "/baca/index/" in href and text:
                full_url = f"https://www.setneg.go.id{href}" if href.startswith('/') else href
                articles[full_url] = text
                
        if not articles:
            print("No articles found on the search page.")
            return

        state = load_state()
        new_announcements = []

        # Keywords that indicate registration is open
        keywords = ["daftar", "pendaftaran", "dibuka", "registrasi", "kuota", "undangan", "hadir"]

        for url, title in articles.items():
            if url not in state:
                # Mark as seen so we don't alert again
                state[url] = title
                
                # Check if the title matches relevant keywords
                if any(kw in title.lower() for kw in keywords):
                    new_announcements.append((title, url))
                    
        # Update local state
        save_state(state)

        # Notify if new matching articles are found
        if new_announcements:
            print(f"Found {len(new_announcements)} new matching announcements!")
            for title, url in new_announcements:
                msg = (
                    f"🚨 *PENGUMUMAN UPACARA BARU DITEMUKAN!*\n\n"
                    f"*Judul:* {title}\n"
                    f"*Link:* {url}"
                )
                print(msg)
                send_telegram_message(msg)
        else:
            print("No new relevant announcements found.")

    except Exception as e:
        print(f"Error checking announcements: {e}")

def main():
    print("Starting bot checker for Independence Day Ceremony Registration...")
    
    # If running in GitHub Actions, exit after single run
    if os.getenv("GITHUB_ACTIONS") == "true":
        print("GitHub Actions detected. Running single check.")
        check_announcements()
        return

    print(f"Interval: {CHECK_INTERVAL} seconds.")
    # Run once immediately
    check_announcements()
    
    # Loop indefinitely
    while True:
        try:
            time.sleep(CHECK_INTERVAL)
            check_announcements()
        except KeyboardInterrupt:
            print("\nStopping bot checker.")
            break
        except Exception as e:
            print(f"Error in main loop: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()
