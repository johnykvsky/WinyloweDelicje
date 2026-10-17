#!/usr/bin/env python3
"""
Fetch and verify original album durations (in seconds) for all albums in js/data.js.
"""
import json
import os
import re
import subprocess
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_JS_PATH = os.path.join(BASE_DIR, "js", "data.js")
DURATIONS_PATH = os.path.join(BASE_DIR, "scripts", "durations_map.json")

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"

# Curated exact original LP/album durations (in seconds) for albums that are
# either missing from streaming, or whose streaming editions are multi-disc Deluxe Editions
# or single/special releases.
CURATED_DURATIONS_SEC = {
    ("Pink Floyd", "The Dark Side of the Moon"): 42 * 60 + 50,         # 42:50
    ("Genesis", "Wind & Wuthering"): 50 * 60 + 55,                     # 50:55
    ("King Crimson", "In the Court of the Crimson King"): 43 * 60 + 56,# 43:56
    ("Electric Light Orchestra", "Out of the Blue"): 70 * 60 + 17,     # 70:17 (2LP)
    ("Jethro Tull", "Minstrel in the Gallery"): 45 * 60 + 12,          # 45:12
    ("Chuck Mangione", "Children of Sanchez"): 81 * 60 + 50,           # 81:50 (2LP)
    ("Roger Waters", "Amused to Death"): 72 * 60 + 45,                 # 72:45
    ("Mike Oldfield", "Tubular Bells"): 48 * 60 + 50,                  # 48:50
    ("Queen", "Innuendo"): 53 * 60 + 44,                               # 53:44
    ("Sting", "Live in Berlin"): 77 * 60 + 18,                         # 77:18
    ("Queen", "Live in Budapest"): 90 * 60 + 0,                        # 90:00
    ("Rick Wakeman", "Journey to the Centre of the Earth"): 40 * 60 + 1,# 40:01
    ("Jon and Vangelis", "The Friends of Mr Cairo"): 41 * 60 + 56,     # 41:56
    ("Jeff Wayne", "Jeff Wayne’s Musical Version of The War of the Worlds"): 94 * 60 + 51, # 94:51 (2LP)
    ("Jeff Wayne", "The Musical Version of The War of the Worlds"): 94 * 60 + 51,          # 94:51 (2LP)
    ("SBB", "Ze słowem biegnę do Ciebie"): 39 * 60 + 27,               # 39:27
    ("SBB", "Memento z banalnym tryptykiem"): 39 * 60 + 50,            # 39:50
    ("SBB", "Za słowem biegnę do Ciebie, Memento z banalnym tryptykiem"): (39 * 60 + 27) + (39 * 60 + 50), # Both albums played
    ("Józef Skrzek", "Ojciec chrzestny Dominika"): 40 * 60 + 5,        # 40:05
    ("Pink Floyd", "The Wall"): 81 * 60 + 9,                           # 81:09 (2LP)
    ("Pendragon", "The Masquerade Overture"): 68 * 60 + 14,            # 68:14
    ("Dead Can Dance", "Anastasis"): 56 * 60 + 5,                      # 56:05
    ("Clive Nolan & Oliver Wakeman", "Jabberwocky"): 58 * 60 + 35,     # 58:35
    ("Jean-Michel Jarre", "Oxygene"): 39 * 60 + 48,                    # 39:48
    ("Dire Straits", "Brothers in Arms"): 55 * 60 + 7,                 # 55:07 (or LP 47:44; standard album 55:07)
    ("Pendragon", "The Window of Life"): 62 * 60 + 38,                 # 62:38
    ("Steven Wilson", "The Raven That Refused to Sing (and Other Stories)"): 54 * 60 + 28,
    ("Steven Wilson", "The Raven That Refused to Sing (And Other Stories)"): 54 * 60 + 28,
    ("Procol Harum", "Grand Hotel"): 41 * 60 + 10,                     # 41:10
    ("The Doors", "The Doors"): 44 * 60 + 28,                          # 44:28
    ("Electric Light Orchestra", "Rock ’n’ Roll Is King"): 3 * 60 + 49,# 3:49 (single)
    ("Sting", "The Soul Cages"): 48 * 60 + 10,                         # 48:10
    ("Yes", "Close to the Edge"): 37 * 60 + 51,                        # 37:51
    ("Mike Oldfield", "Ommadawn"): 36 * 60 + 41,                       # 36:41
    ("Isao Tomita", "The Planets"): 51 * 60 + 55,                      # 51:55
    ("Pink Floyd", "Wish You Were Here"): 44 * 60 + 12,                # 44:12
    ("Dream Theater", "Images and Words"): 57 * 60 + 4,                # 57:04
    ("The Alan Parsons Project", "Tales of Mystery and Imagination"): 41 * 60 + 51, # 41:51
    ("Sade", "Soldier of Love"): 43 * 60 + 5,                          # 43:05
    ("Céline Dion", "All the Way… A Decade of Song"): 74 * 60 + 18,    # 74:18
    ("Jon and Vangelis", "Private Collection"): 46 * 60 + 31,          # 46:31
    ("Emerson, Lake & Palmer", "Tarkus"): 38 * 60 + 55,                # 38:55
    ("Blackfield", "Blackfield"): 39 * 60 + 38,                        # 39:38
    ("Led Zeppelin", "IV"): 42 * 60 + 38,                              # 42:38
    ("Porcupine Tree", "The Sky Moves Sideways"): 65 * 60 + 31,        # 65:31
    ("Pendragon", "Not of This World"): 62 * 60 + 39,                  # 62:39
    ("Marillion", "Script for a Jester’s Tear"): 47 * 60 + 11,         # 47:11
    ("Marillion", "Script for a Jester's Tear"): 47 * 60 + 11,         # 47:11
    ("Fish", "A Feast of Consequences"): 66 * 60 + 45,                 # 66:45
    ("Marek Grechuta", "Korowód"): 39 * 60 + 40,                       # 39:40
    ("Steven Wilson", "Hand. Cannot. Erase."): 65 * 60 + 54,           # 65:54
    ("U2", "Achtung Baby"): 55 * 60 + 27,                              # 55:27
    ("Kraftwerk", "Trans Europa Express"): 42 * 60 + 44,               # 42:44
    ("Jean-Michel Jarre", "Les Concerts en Chine"): 78 * 60 + 20,      # 78:20 (2LP)
    ("Skaldowie", "Krywań, Krywań"): 39 * 60 + 25,                     # 39:25
    ("Frank Sinatra", "Moonlight Sinatra"): 32 * 60 + 24,              # 32:24
    ("Melody Gardot", "My One and Only Thrill"): 47 * 60 + 53,         # 47:53
    ("Focus", "Focus II"): 41 * 60 + 22,                               # 41:22
    ("Camel", "The Snow Goose"): 43 * 60 + 13,                         # 43:13
    ("Skaldowie", "Stworzenia świata część druga"): 39 * 60 + 15,      # 39:15
    ("Exodus", "Ten najpiękniejszy dzień"): 39 * 60 + 46,              # 39:46
    ("Genesis", "…And Then There Were Three…"): 53 * 60 + 27,          # 53:27
    ("Anthony Phillips", "Wise After the Event"): 51 * 60 + 40,        # 51:40
    ("Van der Graaf Generator", "H to He, Who Am the Only One"): 46 * 60 + 50, # 46:50
    ("Queen", "A Day at the Races"): 44 * 60 + 16,                     # 44:16
    ("David Bowie", "Blackstar"): 41 * 60 + 14,                        # 41:14
    ("Weather Report", "Heavy Weather"): 37 * 60 + 42,                 # 37:42
    ("Miles Davis", "Kind of Blue"): 45 * 60 + 44,                     # 45:44
    ("The Manhattan Transfer", "Coming Out"): 37 * 60 + 15,            # 37:15
    ("Dream Theater", "The Astonishing"): 130 * 60 + 23,               # 130:23 (2CD/4LP)
    ("Andreas Vollenweider", "Book of Roses"): 54 * 60 + 24,           # 54:24
    ("Riverside", "Love, Fear and the Time Machine"): 60 * 60 + 14,    # 60:14
    ("Jethro Tull", "Thick as a Brick"): 43 * 60 + 46,                 # 43:46
    ("Yes", "Relayer"): 40 * 60 + 26,                                  # 40:26
    ("Manfred Mann’s Earth Band", "The Roaring Silence"): 39 * 60 + 43,# 39:43
    ("U.K.", "Danger Money"): 41 * 60 + 50,                            # 41:50
    ("The Moody Blues", "On the Threshold of a Dream"): 35 * 60 + 56,  # 35:56
    ("Genesis", "Nursery Cryme"): 39 * 60 + 28,                        # 39:28
    ("SBB", "Za linią horyzontu"): 52 * 60 + 11,                       # 52:11
    ("Vangelis", "Heaven and Hell"): 43 * 60 + 14,                     # 43:14
    ("Kitaro", "Ten Kai"): 49 * 60 + 12,                               # 49:12
    ("Klaus Schulze", "X"): 114 * 60 + 38,                             # 114:38 (2LP)
    ("Leonard Cohen", "Old Ideas"): 41 * 60 + 4,                       # 41:04
    ("Willie Nelson", "Stardust"): 36 * 60 + 48,                       # 36:48
    ("Lacrimosa", "Elodia"): 61 * 60 + 15,                             # 61:15
    ("Marillion", "Fuck Everyone and Run (F E A R)"): 67 * 60 + 56,    # 67:56
    ("Air", "Talkie Walkie"): 45 * 60 + 10,                            # 45:10
    ("Pink Floyd", "Atom Heart Mother"): 52 * 60 + 8,                  # 52:08
    ("Pink Floyd", "Animals"): 41 * 60 + 41,                           # 41:41
    ("Pink Floyd", "Meddle"): 46 * 60 + 48,                            # 46:48
    ("Supertramp", "Crime of the Century"): 44 * 60 + 17,              # 44:17
    ("Mike Oldfield", "Return to Ommadawn"): 42 * 60 + 7,              # 42:07
    ("Depeche Mode", "Spirit"): 49 * 60 + 23,                          # 49:23
    ("Ultravox", "Vienna"): 43 * 60 + 21,                              # 43:21
    ("Fleetwood Mac", "Rumours"): 39 * 60 + 43,                        # 39:43
    ("Chris Rea", "Auberge"): 59 * 60 + 10,                            # 59:10
    ("Beth Hart", "Better Than Home"): 46 * 60 + 38,                   # 46:38
    ("Deep Purple", "Infinite"): 45 * 60 + 37,                         # 45:37
    ("Modest Mussorgsky and Maurice Ravel", "Pictures at an Exhibition"): 34 * 60 + 30, # 34:30
    ("Roger Waters", "The Pros and Cons of Hitch Hiking"): 42 * 60 + 7,# 42:07
    ("Yello", "One Second"): 46 * 60 + 12,                             # 46:12
    ("King Crimson", "Lizard"): 42 * 60 + 30,                          # 42:30
    ("Archive", "Axiom"): 39 * 60 + 37,                                # 39:37
    ("Anathema", "A Natural Disaster"): 56 * 60 + 24,                  # 56:24
    ("Czesław Niemen oraz Akwarele", "Dziwny Jest Ten Świat"): 36 * 60 + 12, # 36:12
    ("Czesław Niemen oraz Akwarele", "Sukces"): 37 * 60 + 45,          # 37:45
    ("Breakout", "Blues"): 39 * 60 + 53,                               # 39:53
    ("Donald Fagen", "The Nightfly"): 38 * 60 + 46,                    # 38:46
    ("Santana", "Abraxas"): 37 * 60 + 31,                              # 37:31
    ("Coldplay", "Ghost Stories"): 42 * 60 + 37,                       # 42:37
    ("Al Di Meola, John McLaughlin, Paco de Lucía", "Friday Night in San Francisco"): 40 * 60 + 43, # 40:43
    ("Dire Straits", "Dire Straits"): 41 * 60 + 34,                    # 41:34
    ("Simon & Garfunkel", "Bridge Over Troubled Water"): 36 * 60 + 29, # 36:29
    ("Marillion", "Fugazi"): 45 * 60 + 57,                             # 45:57
    ("Electric Light Orchestra", "Eldorado: A Symphony by the Electric Light Orchestra"): 42 * 60 + 58, # 42:58
    ("Genesis", "Duke"): 55 * 60 + 6,                                  # 55:06
    ("Electric Light Orchestra", "Secret Messages"): 46 * 60 + 48,     # 46:48
    ("Tangerine Dream", "Stratosfear"): 35 * 60 + 24,                  # 35:24
    ("Klaus Schulze", "Mirage"): 58 * 60 + 16,                         # 58:16
    ("Klaus Schulze", "Timewind"): 59 * 60 + 13,                       # 59:13
    ("Jan A.P. Kaczmarek oraz Orkiestra Ósmego Dnia", "Czekając na kometę Halleya"): 41 * 60 + 20, # 41:20
    ("Komeda Quintet", "Astigmatic"): 45 * 60 + 18,                    # 45:18
    ("Procol Harum", "Shine On Brightly"): 39 * 60 + 21,               # 39:21
    ("The Beatles", "Yellow Submarine"): 40 * 60 + 12,                 # 40:12
    ("Deep Purple", "Stormbringer"): 36 * 60 + 31,                     # 36:31
    ("Roxy Music", "Avalon"): 37 * 60 + 28,                            # 37:28
    ("Norah Jones", "Come Away With Me"): 45 * 60 + 9,                 # 45:09
    ("Supertramp", "Breakfast in America"): 46 * 60 + 6,               # 46:06
    ("Yes", "90125"): 44 * 60 + 47,                                    # 44:47
    ("Adele", "25"): 48 * 60 + 25,                                     # 48:25
    ("The Alan Parsons Project", "Gaudi"): 40 * 60 + 15,               # 40:15
    ("Andrew Lloyd Webber", "The Phantom of the Opera"): 99 * 60 + 15, # 99:15 (2LP)
    ("Led Zeppelin", "II"): 41 * 60 + 24,                              # 41:24
    ("The Beatles", "Abbey Road"): 47 * 60 + 23,                       # 47:23
    ("The Cure", "Disintegration"): 72 * 60 + 14,                      # 72:14
    ("Marek Biliński", "Ogród Króla Świtu"): 38 * 60 + 50,             # 38:50
    ("Marek Biliński", "E≠mc²"): 38 * 60 + 15,                         # 38:15
    ("ABBA", "Super Trouper"): 41 * 60 + 52,                           # 41:52
    ("Bee Gees", "Spirits Having Flown"): 46 * 60 + 22,                # 46:22
    ("Gary Moore", "After the War"): 51 * 60 + 18,                     # 51:18
    ("Eric Clapton", "Pilgrim"): 75 * 60 + 38,                         # 75:38
    ("Halina Frąckowiak", "Geira"): 38 * 60 + 42,                      # 38:42
    ("Mike Oldfield", "Crises"): 36 * 60 + 36,                         # 36:36
    ("Gustav Holst", "The Planets"): 50 * 60 + 12,                     # 50:12
    ("Jean-Michel Jarre", "Zoolook"): 37 * 60 + 54,                    # 37:54
    ("Marek Biliński", "Mały Książę"): 44 * 60 + 25,                   # 44:25
    ("Leonard Cohen", "Ten New Songs"): 52 * 60 + 40,                  # 52:40
    ("Mariza", "Mundo"): 48 * 60 + 32,                                 # 48:32
    ("Rafał Blechacz", "II koncert f-moll op.21"): 32 * 60 + 34,       # 32:34 (f-moll Op. 21)
    ("Czesław Niemen", "Enigmatic"): 38 * 60 + 26,                     # 38:26
    ("ABBA", "Waterloo"): 37 * 60 + 36,                                # 37:36
    ("ABBA", "Voyage"): 36 * 60 + 49,                                  # 36:49
    ("Omega", "Skyrover"): 41 * 60 + 10,                               # 41:10
    ("Beth Hart & Joe Bonamassa", "Don’t Explain"): 46 * 60 + 16,      # 46:16
    ("Jethro Tull", "The Broadsword and the Beast"): 39 * 60 + 14,     # 39:14
    ("Procol Harum", "Something Magic"): 40 * 60 + 12,                 # 40:12
    ("Eloy", "Ocean"): 44 * 60 + 22,                                   # 44:22
    ("Marillion", "Clutching at Straws"): 52 * 60 + 20,                # 52:20
    ("Opeth", "Pale Communion"): 55 * 60 + 42,                         # 55:42
    ("Vangelis", "Blade Runner"): 57 * 60 + 39,                        # 57:39
    ("Rush", "R30: 30th Anniversary World Tour"): 118 * 60 + 30,       # 118:30 (2CD)
    ("Earth, Wind & Fire", "Live In Japan"): 95 * 60 + 0,              # 95:00
    ("Andreas Vollenweider", "The Magical Journey"): 71 * 60 + 12,     # 71:12
    ("Ennio Morricone", "Ennio Morricone In Venice (Live At Piazza San Marco)"): 98 * 60 + 15,
    ("The Alan Parsons Project", "The Turn of a Friendly Card"): 40 * 60 + 8, # 40:08
    ("Deep Purple", "Deep Purple"): 44 * 60 + 15,                      # 44:15
    ("Krzysztof Komeda", "Astigmatic in Concert"): 55 * 60 + 47,       # 55:47
    ("Laboratorium", "No. 8"): 39 * 60 + 10,                           # 39:10
    ("Rush", "2112"): 38 * 60 + 48,                                    # 38:48
    ("Collage", "Over and Out"): 62 * 60 + 5,                          # 62:05
    ("Jeff Beck", "Jeff Beck’s Guitar Shop"): 39 * 60 + 51,            # 39:51
    ("Paul McCartney", "Wings Greatest"): 54 * 60 + 20,                # 54:20
    ("Wishbone Ash", "Argus"): 44 * 60 + 43,                           # 44:43
    ("Camel", "Stationary Traveller"): 42 * 60 + 18,                   # 42:18
    ("Pendragon", "The World"): 56 * 60 + 27,                          # 56:27
    ("Dream Theater", "A View From the Top of the World"): 70 * 60 + 21,# 70:21
    ("Genesis", "…Calling All Stations…"): 67 * 60 + 42,               # 67:42
    ("Peter Gabriel", "So"): 46 * 60 + 15,                             # 46:15
    ("SBB", "Welcome"): 40 * 60 + 18,                                  # 40:18
    ("Tina Turner", "Private Dancer"): 44 * 60 + 1,                    # 44:01
    ("Dream Theater", "Octavarium"): 75 * 60 + 46,                     # 75:46
    ("The Alan Parsons Project", "I Robot"): 41 * 60 + 5,              # 41:05
    ("Genesis", "The Lamb Lies Down on Broadway"): 94 * 60 + 15,       # 94:15 (2LP)
    ("The Beatles", "Now and Then"): 4 * 60 + 8,                       # 4:08 (single)
    ("Obywatel G.C.", "Stan strachu"): 42 * 60 + 35,                   # 42:35
    ("Wojciech Trzciński / Ernest Bryll", "Kolęda Nocka"): 43 * 60 + 15,# 43:15
    ("Led Zeppelin", "Presence"): 44 * 60 + 25,                        # 44:25
    ("Wojciech Kilar", "Bram Stoker’s Dracula: Original Motion Picture Soundtrack"): 55 * 60 + 0,
    ("Ewa Demarczyk", "Ewa Demarczyk śpiewa piosenki Zygmunta Koniecznego"): 41 * 60 + 50,
    ("Jim Ladd", "Innerview: Series 24, Show 08: Pink Floyd, The Final Cut"): 58 * 60 + 0,
    ("The Beatles", "Sgt. Pepper’s Lonely Hearts Club Band"): 39 * 60 + 52, # 39:52
    ("Ennio Morricone", "Ennio (film)"): 112 * 60 + 0,                 # 112:00 (2LP soundtrack)
    ("Céline Dion", "Let’s Talk About Love"): 70 * 60 + 55,            # 70:55
    ("Depeche Mode", "Music for the Masses"): 44 * 60 + 43,            # 44:43
    ("The Doors", "L.A. Woman"): 48 * 60 + 25,                         # 48:25
    ("Kylie Minogue", "Aphrodite Les Folies - Live in London O2 Arena"): 119 * 60 + 20,
    ("Pink Floyd", "The Piper at the Gates of Dawn"): 41 * 60 + 52,    # 41:52
    ("Genesis", "A Trick of the Tail"): 51 * 60 + 5,                   # 51:05
    ("Electric Light Orchestra", "A New World Record"): 36 * 60 + 20,  # 36:20
    ("Electric Light Orchestra", "Face The Music"): 36 * 60 + 24,      # 36:24
    ("Ennio Morricone", "Once Upon a Time in America"): 49 * 60 + 18,  # 49:18
    ("Neil Diamond", "All-Time Greatest Hits"): 78 * 60 + 10,          # 78:10
    ("Procol Harum", "A Whiter Shade of Pale"): 4 * 60 + 9,            # 4:09 (single)
    ("Jethro Tull", "Heavy Horses"): 41 * 60 + 20,                     # 41:20
    ("Breakout", "Karate"): 40 * 60 + 15,                              # 40:15
}


def fetch_duration_from_api(artist: str, album: str) -> int:
    """Automatically fetch album duration in seconds from Deezer or iTunes for newly added albums."""
    if not album or artist in ("Uroki PRL", "Legendy światowego jazzu", "Jubileusz 100"):
        return 0
    q = urllib.parse.quote(f'artist:"{artist}" album:"{album}"')
    try:
        out = subprocess.check_output(
            ["curl", "-sL", "-A", UA, f"https://api.deezer.com/search/album?q={q}&limit=5"],
            timeout=10,
        ).decode("utf-8", errors="replace")
        data = json.loads(out)
        for item in data.get("data", []):
            alb_id = item.get("id")
            if alb_id:
                alb_out = subprocess.check_output(
                    ["curl", "-sL", "-A", UA, f"https://api.deezer.com/album/{alb_id}"],
                    timeout=10,
                ).decode("utf-8", errors="replace")
                alb_data = json.loads(alb_out)
                dur = int(alb_data.get("duration") or 0)
                if dur > 0:
                    return dur
    except Exception:
        pass
    return 0


def main():
    with open(DATA_JS_PATH, "r", encoding="utf-8") as f:
        text = f.read()

    prefix = "window.WINYLOWE_DATA = "
    meetings = json.loads(text[text.index(prefix) + len(prefix):].rstrip().rstrip(";"))

    missing = []
    updated = 0
    for m in meetings:
        for a in m.get("albums", []):
            key = (a["artist"], a["album"])
            sec = CURATED_DURATIONS_SEC.get(key)
            if sec is None and a.get("durationSeconds"):
                sec = int(a["durationSeconds"])
            if sec is None and a["album"]:
                sec = fetch_duration_from_api(a["artist"], a["album"])
                if sec > 0:
                    print(f"Auto-fetched duration for new album {key}: {sec // 60}:{sec % 60:02d}")
            if sec:
                a["durationSeconds"] = sec
                updated += 1
            else:
                a["durationSeconds"] = 0
                if a["album"] and a["artist"] not in ("Uroki PRL", "Legendy światowego jazzu", "Jubileusz 100"):
                    missing.append(key)

    with open(DATA_JS_PATH, "w", encoding="utf-8") as f:
        f.write("// Winylowe Delicje — meetings and albums dataset (covers, genres, durations)\n")
        f.write("window.WINYLOWE_DATA = " + json.dumps(meetings, ensure_ascii=False, indent=2) + ";\n")

    print(f"Updated {updated} album entries with durationSeconds. Missing album entries: {len(missing)}")
    if missing:
        for m in missing:
            print("  Missing:", m)


if __name__ == "__main__":
    main()
