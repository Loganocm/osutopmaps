import json
import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.webdriver import WebDriver
from webdriver_manager.chrome import ChromeDriverManager
from mods import get_mods_from_bitwise  # Import the function from mods.py
from decimal import Decimal, ROUND_HALF_UP

# JSON File for storing top players and best plays
JSON_FILE = "C:\\Users\\Logan\\Desktop\\osutopmaps\\top50.json"

# osu! API key (replace with your actual key)
API_KEY = "96ab088730fee625bca2d6af9ba139be98ef2406"

# Load previous players from JSON
def load_previous_players():
    try:
        with open(JSON_FILE, "r") as file:
            data = json.load(file)
            if not isinstance(data, dict):
                data = {}
            if "players" not in data:
                data["players"] = []
            return {player["name"]: player["url"] for player in data["players"]}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_players(players, best_plays=None):
    data = {"players": []}

    for name, url in players.items():
        best_plays_for_player = best_plays.get(name, []) if best_plays else []
        
        # No need to split mods as they are already a list from `get_mods_from_bitwise`
        data["players"].append({
            "name": name,
            "url": url,
            "best_plays": best_plays_for_player
        })

    print(f"Saving data to JSON: {json.dumps(data, indent=4)}")

    try:
        with open(JSON_FILE, "w", encoding='utf-8') as file:
            json.dump(data, file, indent=4)
        print(f"Data successfully saved to {JSON_FILE}")
    except Exception as e:
        print(f"Error saving data: {e}")

# Set up headless Selenium WebDriver
def setup_driver() -> WebDriver:
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

# Scrape the osu! top 50 players
def scrape_top_players():
    driver = setup_driver()
    url = "https://osu.ppy.sh/rankings/osu/performance"
    driver.get(url)
    time.sleep(3)

    player_elements = driver.find_elements(By.CSS_SELECTOR, "a.ranking-page-table__user-link-text.js-usercard")
    players = {player.text.strip(): player.get_attribute("href") for player in player_elements}
    
    driver.quit()
    return players

# Fetch the top 10 best plays for a user using osu! API
def get_best_plays(user_name):
    if user_name.startswith("https://osu.ppy.sh/users/"):
        user_id = user_name.split('/')[-2]

    print(f"Fetching best plays for user ID: {user_id}")
    
    url = f"https://osu.ppy.sh/api/get_user_best"
    params = {
        'u': user_id,
        'k': API_KEY,
        'limit': 5
    }

    response = requests.get(url, params=params)

    if response.status_code != 200:
        print(f"Error fetching best plays: {response.status_code}")
        return []

    data = response.json()
    
    if not data:
        print(f"No best plays found for user {user_name}")
        return []

    best_plays = []
    for play in data:
        print(f"Processing play: {play}")
        beatmap_url = f"https://osu.ppy.sh/api/get_beatmaps"
        beatmap_params = {
            'k': API_KEY,
            'b': play['beatmap_id']
        }
        beatmap_response = requests.get(beatmap_url, params=beatmap_params)

        if beatmap_response.status_code == 200:
            beatmap_data = beatmap_response.json()

            if beatmap_data:
                beatmap = beatmap_data[0]

                count_300 = int(play['count300'])
                count_50 = int(play['count50'])
                count_100 = int(play['count100'])
                count_miss = int(play['countmiss'])
                total_hits = count_300 + count_50 + count_100 + count_miss

                if total_hits > 0:
                    accuracy = (count_300 * 300.0 + count_100 * 100.0 + count_50 * 50.0) / (total_hits * 300.0)
                else:
                    accuracy = 0.0

                # Round accuracy to 4 significant figures
                accuracy_decimal = Decimal(accuracy).quantize(Decimal('1e-4'), rounding=ROUND_HALF_UP)

                # Convert to percentage
                accuracy_percentage = accuracy_decimal * 100

                # Format to two decimal places as a percentage
                formatted_accuracy = f"{accuracy_percentage:.2f}%"

                difficulty_rating = float(beatmap['difficultyrating'])
                diff_aim = float(beatmap['diff_aim'])
                diff_speed = float(beatmap['diff_speed'])
                diff_size = float(beatmap['diff_size'])
                diff_overall = float(beatmap['diff_overall'])
                diff_approach = float(beatmap['diff_approach'])
                diff_drain = float(beatmap['diff_drain'])

                mods = get_mods_from_bitwise(int(play['enabled_mods']))  # Use the new function to get mods
                
                best_plays.append({
                    'title': beatmap['title'],
                    'artist': beatmap['artist'],
                    'accuracy': formatted_accuracy,  # Store formatted accuracy as percentage
                    'pp': float(play['pp']),
                    'score': play['score'],
                    'date': play['date'],
                    'difficulty_rating': difficulty_rating,
                    'diff_aim': diff_aim,
                    'diff_speed': diff_speed,
                    'diff_size': diff_size,
                    'diff_overall': diff_overall,
                    'diff_approach': diff_approach,
                    'diff_drain': diff_drain,
                    'version': beatmap['version'],
                    'mods': mods  # Add mods to the play details
                })
            else:
                print(f"No beatmap details found for beatmap_id {play['beatmap_id']}")
        else:
            print(f"Error fetching beatmap details for beatmap ID {play['beatmap_id']}")

    # Sort best plays by PP in descending order
    best_plays.sort(key=lambda x: x['pp'], reverse=True)
    
    return best_plays

# Compare old and new player lists
def compare_players(old_players, new_players):
    old_set, new_set = set(old_players.keys()), set(new_players.keys())

    added_players = new_set - old_set
    removed_players = old_set - new_set

    return added_players, removed_players

# Main execution
if __name__ == "__main__":
    old_players = load_previous_players()
    new_players = scrape_top_players()

    added, removed = compare_players(old_players, new_players)

    if added:
        print("\n🟢 New Players Added:")
        for name in added:
            print(f"- {name}: {new_players[name]}")

    if removed:
        print("\n🔴 Players Removed:")
        for name in removed:
            print(f"- {name}: {old_players[name]}")

    best_plays_dict = {}
    for name, url in new_players.items():
        print(f"\nFetching best plays for: {name}")

        best_plays = get_best_plays(url)
        best_plays_dict[name] = best_plays

        for play in best_plays:
            print(f"Title: {play['title']}, Artist: {play['artist']}, Accuracy: {play['accuracy']}, PP: {play['pp']}, Mods: {', '.join(play['mods'])}, Performance Date: {play['date']}")

    save_players(new_players, best_plays_dict)
    print("\n💾 Player data and best plays updated successfully!")