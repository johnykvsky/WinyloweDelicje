#!/usr/bin/env python3
"""
Unified cover fetcher & optimizer for Winylowe Delicje.
- Reads js/data.js directly (no CSV dependency, preserves genre, durationSeconds, etc.).
- Skips albums that already have an existing cover image in assets/covers/ (unless --force is used).
- For any new/missing album cover, strictly verifies Artist + Album across curated URLs,
  iTunes, Deezer, MusicBrainz Cover Art Archive, and Wikipedia.
- Automatically optimizes and resizes downloaded covers (200px shorter side, RGB JPEG quality 85).
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import unicodedata
import urllib.parse
import urllib.request
from PIL import Image

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COVERS_DIR = os.path.join(BASE_DIR, "assets", "covers")
DATA_JS_PATH = os.path.join(BASE_DIR, "js", "data.js")

os.makedirs(COVERS_DIR, exist_ok=True)

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
TARGET_MIN_SIDE = 200
JPEG_QUALITY = 85

BANNED_ARTIST_TERMS = [
    "tribute", "karaoke", "lullaby", "8-bit", "string quartet",
    "vitamin", "twinkle twinkle", "piano guys", "rockabye",
    "made famous", "in the style of", "cover", "backing track",
    "orgel", "music box", "symphonic rock", "pink floydisch"
]

VERIFIED_DIRECT_URLS = {
    ("Andrew Lloyd Webber", "The Phantom of the Opera"): "https://cdn-images.dzcdn.net/images/cover/00c4d216ed13fd40516c2ad3c11f9dbb/500x500-000000-80-0-0.jpg",
    ("Dire Straits", "Dire Straits"): "https://cdn-images.dzcdn.net/images/cover/1bf2bc47623db2ec36a38be064131ce5/500x500-000000-80-0-0.jpg",
    ("Donald Fagen", "The Nightfly"): "https://cdn-images.dzcdn.net/images/cover/321897fe378c1c9c8250f74bfab78e94/500x500-000000-80-0-0.jpg",
    ("Eloy", "Ocean"): "https://cdn-images.dzcdn.net/images/cover/fe414a0580202b3a779aefbeabf14e6e/500x500-000000-80-0-0.jpg",
    ("Fleetwood Mac", "Rumours"): "https://cdn-images.dzcdn.net/images/cover/9732751ce91d786dcf30069853697078/500x500-000000-80-0-0.jpg",
    ("Marillion", "Script for a Jester's Tear"): "https://cdn-images.dzcdn.net/images/cover/7925b0bd5db7d66098cb405110e201b4/500x500-000000-80-0-0.jpg",
    ("Marillion", "Script for a Jester’s Tear"): "https://cdn-images.dzcdn.net/images/cover/7925b0bd5db7d66098cb405110e201b4/500x500-000000-80-0-0.jpg",
    ("Pendragon", "The World"): "https://coverartarchive.org/release-group/70490cc0-916f-3f6a-996e-79e04f2ef442/front-500",
    ("Peter Gabriel", "So"): "https://cdn-images.dzcdn.net/images/cover/5f6501830e0fd1309550d25dd2056c18/500x500-000000-80-0-0.jpg",
    ("Roxy Music", "Avalon"): "https://cdn-images.dzcdn.net/images/cover/803d977d40eb4c895a50810857829d0b/500x500-000000-80-0-0.jpg",
    ("The Alan Parsons Project", "Gaudi"): "https://cdn-images.dzcdn.net/images/cover/170bd9c3f342fd8081ff5d3f0031acff/500x500-000000-80-0-0.jpg",
    ("The Cure", "Disintegration"): "https://cdn-images.dzcdn.net/images/cover/6695e76996cb8ef9529ff70a65404329/500x500-000000-80-0-0.jpg",
    ("The Doors", "L.A. Woman"): "https://cdn-images.dzcdn.net/images/cover/03f8ae4438cbf73c1e1cc435123deb72/500x500-000000-80-0-0.jpg",
    ("The Doors", "The Doors"): "https://cdn-images.dzcdn.net/images/cover/a58f4c70b9c51b8902be3f2e875155fe/500x500-000000-80-0-0.jpg",
    ("Willie Nelson", "Stardust"): "https://cdn-images.dzcdn.net/images/cover/8fc2e9a1d74e769920d3aa62a52f44c7/500x500-000000-80-0-0.jpg",
    ("U.K.", "Danger Money"): "https://cdn-images.dzcdn.net/images/cover/1f27277ae8202f2c49a9b1fe9b0fc17e/500x500-000000-80-0-0.jpg",
    ("Exodus", "Ten najpiękniejszy dzień"): "https://cdn-images.dzcdn.net/images/cover/f6d9b85c8172d26c3978d873e8508229/500x500-000000-80-0-0.jpg",
    ("Rush", "R30: 30th Anniversary World Tour"): "https://cdn-images.dzcdn.net/images/cover/398c8d85633c845a7a04c3d072c33cda/500x500-000000-80-0-0.jpg",
    ("Jim Ladd", "Innerview: Series 24, Show 08: Pink Floyd, The Final Cut"): "https://cdn-images.dzcdn.net/images/cover/8786a773304efc7b1b6906f154096b79/500x500-000000-80-0-0.jpg",
    ("Ennio Morricone", "Once Upon a Time in America"): "https://coverartarchive.org/release-group/c2251d5e-eb5d-355d-9080-31ce1e1e3ce8/front-500",
    ("Ennio Morricone", "Ennio Morricone In Venice (Live At Piazza San Marco)"): "https://coverartarchive.org/release/72dbd76e-6986-4b3c-86a5-36bfd5ef679e/front-500",
    ("Ennio Morricone", "Ennio (film)"): "https://upload.wikimedia.org/wikipedia/en/e/e0/Ennio_poster.jpg",
    ("Czesław Niemen oraz Akwarele", "Dziwny Jest Ten Świat"): "https://coverartarchive.org/release/7d26d097-b4f1-4e52-882a-c79ae574e25a/front-500",
    ("Ewa Demarczyk", "Ewa Demarczyk śpiewa piosenki Zygmunta Koniecznego"): "https://coverartarchive.org/release-group/1b8872cf-058c-3b57-b701-8828142a405c/front-500",
    ("Obywatel G.C.", "Stan strachu"): "https://coverartarchive.org/release-group/6b71fe3f-025d-3bc2-a7eb-c6512a9e99c5/front-500",
    ("Kitaro", "Ten Kai"): "https://coverartarchive.org/release-group/7a302743-ff11-3c5d-891a-b46c981e5992/front-500",
    ("Krzysztof Komeda", "Astigmatic in Concert"): "https://coverartarchive.org/release-group/4422a1f9-7794-3625-909f-b136343044fd/front-500",
    ("Electric Light Orchestra", "Rock ’n’ Roll Is King"): "https://upload.wikimedia.org/wikipedia/en/0/0a/Rock%27n%27Roll_Is_King.jpg",
    ("Wojciech Trzciński / Ernest Bryll", "Kolęda Nocka"): "https://popmaster.pl/environment/cache/images/productGfx_81534_500_500/Ernest-Bryll%2C-Wojciech-Trzcinski--Koleda-Nocka-Pronit--SLP-4017.jpg",
    ("Jan A.P. Kaczmarek oraz Orkiestra Ósmego Dnia", "Czekając na kometę Halleya"): "https://i.ytimg.com/vi/tztz7IMVPxo/hqdefault.jpg",
}

CANONICAL_OVERRIDES = {
    ("Led Zeppelin", "IV"): ("Led Zeppelin", "Led Zeppelin IV"),
    ("Led Zeppelin", "II"): ("Led Zeppelin", "Led Zeppelin II"),
    ("Focus", "Focus II"): ("Focus", "Moving Waves"),
    ("Kitaro", "Ten Kai"): ("Kitaro", "Astral Voyage"),
    ("Klaus Schulze", "X"): ("Klaus Schulze", "X"),
    ("Marillion", "Fuck Everyone and Run (F E A R)"): ("Marillion", "F E A R"),
    ("Electric Light Orchestra", "Eldorado: A Symphony by the Electric Light Orchestra"): ("Electric Light Orchestra", "Eldorado"),
    ("Jeff Wayne", "Jeff Wayne’s Musical Version of The War of the Worlds"): ("Jeff Wayne", "The War of the Worlds"),
    ("Jeff Wayne", "The Musical Version of The War of the Worlds"): ("Jeff Wayne", "The War of the Worlds"),
    ("Rafał Blechacz", "II koncert f-moll op.21"): ("Rafał Blechacz", "Chopin: The Piano Concertos"),
    ("Ennio Morricone", "Ennio Morricone In Venice (Live At Piazza San Marco)"): ("Ennio Morricone", "Peace Notes: Live in Venice"),
    ("Ennio Morricone", "Ennio (film)"): ("Ennio Morricone", "Ennio"),
    ("Kylie Minogue", "Aphrodite Les Folies - Live in London O2 Arena"): ("Kylie Minogue", "Aphrodite Les Folies: Live in London"),
    ("SBB", "Za słowem biegnę do Ciebie, Memento z banalnym tryptykiem"): ("SBB", "Ze słowem biegnę do Ciebie"),
    ("Czesław Niemen oraz Akwarele", "Dziwny Jest Ten Świat"): ("Czesław Niemen", "Dziwny jest ten świat"),
    ("Czesław Niemen oraz Akwarele", "Sukces"): ("Czesław Niemen", "Sukces"),
    ("Wojciech Trzciński / Ernest Bryll", "Kolęda Nocka"): ("Wojciech Trzciński", "Kolęda Nocka"),
    ("Jan A.P. Kaczmarek oraz Orkiestra Ósmego Dnia", "Czekając na kometę Halleya"): ("Orkiestra Ósmego Dnia", "Czekając na kometę Halleya"),
    ("Wojciech Kilar", "Bram Stoker’s Dracula: Original Motion Picture Soundtrack"): ("Wojciech Kilar", "Bram Stoker's Dracula"),
    ("Modest Mussorgsky and Maurice Ravel", "Pictures at an Exhibition"): ("Modest Mussorgsky", "Pictures at an Exhibition"),
}


def norm(s: str) -> str:
    if not s:
        return ""
    pl_map = str.maketrans("ąćęłńóśźżĄĆĘŁŃÓŚŹŻ", "acelnoszzacelnoszz")
    s = s.translate(pl_map)
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    s = s.lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def tokens(s: str) -> set[str]:
    n = norm(s)
    stop = {"the", "and", "of", "in", "to", "a", "an", "for", "on", "at", "by", "with", "oraz"}
    toks = {t for t in n.split() if t not in stop and len(t) > 1}
    return toks if toks else (set(n.split()) if n else set())


def artist_matches(expected_artist: str, candidate_artist: str) -> bool:
    cand_norm = norm(candidate_artist)
    exp_norm = norm(expected_artist)
    if not cand_norm or not exp_norm:
        return False
    for bad in BANNED_ARTIST_TERMS:
        if bad in cand_norm and bad not in exp_norm:
            return False
    if exp_norm == cand_norm or exp_norm in cand_norm or cand_norm in exp_norm:
        return True
    exp_toks = tokens(expected_artist)
    cand_toks = tokens(candidate_artist)
    if exp_toks and cand_toks and len(exp_toks & cand_toks) >= min(2, len(exp_toks)):
        return True
    return False


def album_matches(expected_album: str, candidate_album: str) -> bool:
    cand_norm = norm(candidate_album)
    exp_norm = norm(expected_album)
    if not cand_norm or not exp_norm:
        return False
    for bad in ["tribute", "karaoke", "lullaby", "8 bit", "in the style"]:
        if bad in cand_norm and bad not in exp_norm:
            return False
    cand_clean = re.sub(
        r"\b(remaster(ed)?|deluxe|expanded|anniversary|edition|version|bonus|special|live at.*|original motion picture.*)\b",
        "",
        cand_norm,
    ).strip()
    cand_clean = re.sub(r"\s+", " ", cand_clean)
    if exp_norm in (cand_norm, cand_clean):
        return True
    if (exp_norm in cand_norm or cand_clean in exp_norm) and len(cand_clean) >= max(2, len(exp_norm) // 2):
        return True
    exp_toks = tokens(expected_album)
    cand_toks = tokens(candidate_album)
    if exp_toks and cand_toks:
        overlap = exp_toks & cand_toks
        if len(overlap) == len(exp_toks) or (len(exp_toks) >= 3 and len(overlap) >= len(exp_toks) - 1):
            return True
    return False


def fetch_json(url: str, timeout: int = 10):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def get_search_pair(artist: str, album: str) -> tuple[str, str]:
    return CANONICAL_OVERRIDES.get((artist, album), (artist, album))


def search_itunes_strict(artist: str, album: str):
    s_art, s_alb = get_search_pair(artist, album)
    for country in ("PL", "US", "GB"):
        q = urllib.parse.quote(f"{s_art} {s_alb}")
        url = f"https://itunes.apple.com/search?term={q}&country={country}&entity=album&limit=15"
        try:
            data = fetch_json(url)
            for r in data.get("results", []):
                cand_art = r.get("artistName", "")
                cand_alb = r.get("collectionName", "")
                art_url = r.get("artworkUrl100", "")
                if art_url and (artist_matches(artist, cand_art) or artist_matches(s_art, cand_art)) and (
                    album_matches(album, cand_alb) or album_matches(s_alb, cand_alb)
                ):
                    return art_url.replace("100x100bb", "600x600bb")
        except Exception:
            pass
    return None


def search_deezer_strict(artist: str, album: str):
    s_art, s_alb = get_search_pair(artist, album)
    for raw_q in (f'artist:"{s_art}" album:"{s_alb}"', f"{s_art} {s_alb}"):
        q = urllib.parse.quote(raw_q)
        url = f"https://api.deezer.com/search/album?q={q}&limit=15"
        try:
            data = fetch_json(url)
            for r in data.get("data", []):
                cand_art = (r.get("artist") or {}).get("name", "")
                cand_alb = r.get("title", "")
                cov = r.get("cover_big") or r.get("cover_medium")
                if cov and (artist_matches(artist, cand_art) or artist_matches(s_art, cand_art)) and (
                    album_matches(album, cand_alb) or album_matches(s_alb, cand_alb)
                ):
                    return cov
        except Exception:
            pass
    return None


def search_musicbrainz_strict(artist: str, album: str):
    s_art, s_alb = get_search_pair(artist, album)
    for query_str in (
        f'artist:"{s_art}" AND releasegroup:"{s_alb}"',
        f'artist:"{artist}" AND releasegroup:"{album}"',
    ):
        q = urllib.parse.quote(query_str)
        url = f"https://musicbrainz.org/ws/2/release-group/?query={q}&fmt=json&limit=10"
        try:
            data = fetch_json(url)
            for rg in data.get("release-groups", []):
                rg_id = rg.get("id")
                rg_title = rg.get("title", "")
                ac = rg.get("artist-credit", [])
                cand_art = " ".join(
                    c.get("name", "") or (c.get("artist") or {}).get("name", "")
                    for c in ac
                    if isinstance(c, dict)
                )
                if (artist_matches(artist, cand_art) or artist_matches(s_art, cand_art)) and (
                    album_matches(album, rg_title) or album_matches(s_alb, rg_title)
                ):
                    caa_url = f"https://coverartarchive.org/release-group/{rg_id}/front-500"
                    try:
                        req = urllib.request.Request(caa_url, headers={"User-Agent": USER_AGENT})
                        with urllib.request.urlopen(req, timeout=8) as resp:
                            if resp.status == 200:
                                return caa_url
                    except Exception:
                        continue
        except Exception:
            pass
    return None


def search_wikipedia_image(artist: str, album: str):
    s_art, s_alb = get_search_pair(artist, album)
    for lang in ("pl", "en"):
        for q_str in (f"{s_art} {s_alb}", f"{s_alb} ({s_art})", s_alb):
            q = urllib.parse.quote(q_str)
            search_url = f"https://{lang}.wikipedia.org/w/api.php?action=query&list=search&srsearch={q}&format=json&srlimit=3"
            try:
                sdata = fetch_json(search_url)
                for hit in sdata.get("query", {}).get("search", []):
                    title = hit.get("title", "")
                    if not (album_matches(album, title) or album_matches(s_alb, title)):
                        continue
                    t_enc = urllib.parse.quote(title)
                    img_url = f"https://{lang}.wikipedia.org/w/api.php?action=query&titles={t_enc}&prop=pageimages&format=json&pithumbsize=500"
                    idata = fetch_json(img_url)
                    for p in idata.get("query", {}).get("pages", {}).values():
                        thumb = (p.get("thumbnail") or {}).get("source")
                        if thumb and not any(x in thumb.lower() for x in ["commons-logo", "flag_of", "icon", "disambig"]):
                            return thumb
            except Exception:
                pass
    return None


def slugify(artist: str, album: str) -> str:
    raw = f"{artist}-{album}".lower()
    pl_map = str.maketrans("ąćęłńóśźż", "acelnoszz")
    raw = raw.translate(pl_map)
    slug = re.sub(r"[^a-z0-9]+", "-", raw).strip("-")
    h = hashlib.md5(f"{artist}|{album}".encode("utf-8")).hexdigest()[:8]
    return f"{slug[:60]}-{h}"


def download_and_optimize_image(url: str, dest: str) -> bool:
    try:
        subprocess.run(
            ["curl", "-sL", "-A", USER_AGENT, "-o", dest, url],
            check=True,
            timeout=15,
        )
        if not os.path.exists(dest) or os.path.getsize(dest) <= 1500:
            return False

        with Image.open(dest) as img:
            w, h = img.size
            if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
                rgba = img.convert("RGBA")
                bg = Image.new("RGB", rgba.size, (25, 28, 36))
                bg.paste(rgba, mask=rgba.split()[3])
                img = bg
            elif img.mode != "RGB":
                img = img.convert("RGB")

            short_side = min(w, h)
            if short_side > TARGET_MIN_SIDE:
                scale = TARGET_MIN_SIDE / float(short_side)
                new_w = max(TARGET_MIN_SIDE, int(round(w * scale)))
                new_h = max(TARGET_MIN_SIDE, int(round(h * scale)))
                img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

            tmp_path = dest + ".tmp.jpg"
            img.save(tmp_path, format="JPEG", quality=JPEG_QUALITY, optimize=True, progressive=True)
        os.replace(tmp_path, dest)
        return True
    except Exception:
        return False


def is_thematic_or_empty(artist: str, album: str) -> bool:
    if not album:
        return True
    if artist in ("Uroki PRL", "Legendy światowego jazzu", "Jubileusz 100"):
        return True
    return False


def resolve_cover_url(artist: str, album: str) -> str | None:
    if (artist, album) in VERIFIED_DIRECT_URLS:
        return VERIFIED_DIRECT_URLS[(artist, album)]
    for fn in (search_itunes_strict, search_deezer_strict, search_musicbrainz_strict, search_wikipedia_image):
        url = fn(artist, album)
        if url:
            return url
    return None


def main():
    force = "--force" in sys.argv
    with open(DATA_JS_PATH, "r", encoding="utf-8") as f:
        text = f.read()

    prefix = "window.WINYLOWE_DATA = "
    meetings = json.loads(text[text.index(prefix) + len(prefix):].rstrip().rstrip(";"))

    cache = {}
    already_ok = 0
    downloaded = 0
    missing = []

    for m in meetings:
        for a in m.get("albums", []):
            art = a.get("artist", "").strip()
            alb = a.get("album", "").strip()
            if is_thematic_or_empty(art, alb):
                continue

            existing_cov = a.get("cover")
            if not force and existing_cov and os.path.exists(os.path.join(BASE_DIR, existing_cov)):
                cache[(art, alb)] = existing_cov
                already_ok += 1
                continue

            if (art, alb) in cache:
                a["cover"] = cache[(art, alb)]
                continue

            slug = slugify(art, alb)
            rel_path = f"assets/covers/{slug}.jpg"
            full_path = os.path.join(BASE_DIR, rel_path)

            url = resolve_cover_url(art, alb)
            if url and download_and_optimize_image(url, full_path):
                a["cover"] = rel_path
                cache[(art, alb)] = rel_path
                downloaded += 1
                print(f"Downloaded & optimized cover: {art} - {alb} -> {rel_path}")
            else:
                missing.append((art, alb))

    if downloaded > 0:
        with open(DATA_JS_PATH, "w", encoding="utf-8") as f:
            f.write("// Winylowe Delicje — meetings and albums dataset (covers, genres, durations)\n")
            f.write("window.WINYLOWE_DATA = " + json.dumps(meetings, ensure_ascii=False, indent=2) + ";\n")

    print(f"Covers check complete: {already_ok} existing OK, {downloaded} newly downloaded, {len(missing)} missing.")
    for art, alb in missing:
        print(f"  Missing cover: {art} - {alb}")


if __name__ == "__main__":
    main()
