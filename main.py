import json
import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.webdriver import WebDriver
from webdriver_manager.chrome import ChromeDriverManager
from mods import get_mods_from_bitwise
from decimal import Decimal, ROUND_HALF_UP
import sqlite3
from dotenv import load_dotenv
import os

osupath = __file__
osudirectory = osupath.rsplit("\\", 1)[0]
DATABASE_FILE = osudirectory + "\\osu_top_players.db"
ENV_FILE = osudirectory + "\\.env"
load_dotenv(dotenv_path=ENV_FILE)
API_KEY = os.getenv("osuapi")

def connect_db():
    conn = sqlite3.connect(DATABASE_FILE)
    return conn

def create_tables():
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute('''CREATE TABLE IF NOT EXISTS map_difficulties (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        map_title TEXT NOT NULL,
                        map_artist TEXT NOT NULL,
                        difficulty_version TEXT NOT NULL,
                        frequency INTEGER DEFAULT 0,
                        UNIQUE(map_title, map_artist, difficulty_version)
                      )''')

    conn.commit()
    conn.close()

def save_map_difficulties_to_db(best_plays=None):
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("UPDATE map_difficulties SET frequency = 0")


    if best_plays:
        for plays in best_plays.values():
            for play in plays:
                map_title = play['title']
                map_artist = play['artist']
                difficulty_version = play['version']
                cursor.execute('''INSERT INTO map_difficulties (map_title, map_artist, difficulty_version, frequency)
                                  VALUES (?, ?, ?, 1)
                                  ON CONFLICT(map_title, map_artist, difficulty_version) 
                                  DO UPDATE SET frequency = frequency + 1''',
                               (map_title, map_artist, difficulty_version))

    conn.commit()
    conn.close()

def load_previous_players_from_db():
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute('SELECT name, url FROM players')
    players = {row[0]: row[1] for row in cursor.fetchall()}

    conn.close()
    return players

def setup_driver() -> WebDriver:
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

def scrape_top_players():
    driver = setup_driver()
    url = "https://osu.ppy.sh/rankings/osu/performance"
    driver.get(url)
    time.sleep(3)

    player_elements = driver.find_elements(By.CSS_SELECTOR, "a.ranking-page-table__user-link-text.js-usercard")
    players = {player.text.strip(): player.get_attribute("href") for player in player_elements}
    
    driver.quit()
    return players

def get_best_plays(user_name):
    if user_name.startswith("https://osu.ppy.sh/users/"):
        user_id = user_name.split('/')[-2]

    print(f"Fetching best plays for user ID: {user_id}")
    
    url = f"https://osu.ppy.sh/api/get_user_best"
    params = {
        'u': user_id,
        'k': API_KEY,
        'limit': 50
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

                accuracy_decimal = Decimal(accuracy).quantize(Decimal('1e-4'), rounding=ROUND_HALF_UP)

                accuracy_percentage = accuracy_decimal * 100

                formatted_accuracy = f"{accuracy_percentage:.2f}%"

                difficulty_rating = float(beatmap['difficultyrating'])
                diff_aim = float(beatmap['diff_aim'])
                diff_speed = float(beatmap['diff_speed'])
                diff_size = float(beatmap['diff_size'])
                diff_overall = float(beatmap['diff_overall'])
                diff_approach = float(beatmap['diff_approach'])
                diff_drain = float(beatmap['diff_drain'])

                mods = get_mods_from_bitwise(int(play['enabled_mods']))
                
                best_plays.append({
                    'title': beatmap['title'],
                    'artist': beatmap['artist'],
                    'accuracy': formatted_accuracy,
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
                    'mods': mods
                })
            else:
                print(f"No beatmap details found for beatmap_id {play['beatmap_id']}")
        else:
            print(f"Error fetching beatmap details for beatmap ID {play['beatmap_id']}")


    best_plays.sort(key=lambda x: x['pp'], reverse=True)
    
    return best_plays

def compare_players(old_players, new_players):
    old_set, new_set = set(old_players.keys()), set(new_players.keys())

    added_players = new_set - old_set
    removed_players = old_set - new_set

    return added_players, removed_players

if __name__ == "__main__":
    create_tables()

    old_players = load_previous_players_from_db()
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

    save_map_difficulties_to_db(best_plays_dict)
    print("\n💾 Map-Difficulty frequency data updated successfully!")