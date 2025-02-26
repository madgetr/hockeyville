# https://hockeyville.kraftheinz.com/api/contest/gallery?country=CA&page=1&pageCount=1000&search=&sort=random&types=story,video,note,photo
import json
import requests
import time
from collections import Counter
from tqdm import tqdm

# SAVE_DIR = "/mnt/c/Users/trevo/OneDrive/Documents/hockeyville_data/"
SAVE_DIR = "data/"
type_point_map = {
    "story": 10,
    "video": 10,
    "note": 1,
    "photo": 3
}

type_limit_map = {
    "story": 1,
    "video": 1,
    "note": 1,
    "photo": 5
}


def fetch_hockeyville_data(cookie):
    url = "https://hockeyville.kraftheinz.com/api/contest/gallery?country=CA&page=1&pageCount=40000&search=&types=story,video,note,photo"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
        "Cookie": cookie
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    try:
        return response.json()
    except requests.exceptions.JSONDecodeError:
        print(response.content)
        raise ValueError("Response content is not valid JSON or is empty")


def get_points_per_facility(data):
    stories = Counter()
    videos = Counter()
    photos = Counter()
    notes = Counter()
    reactions = Counter()
    points = Counter()
    contributors = {}
    facility_names = {}
    reacts_to_ours = 0
    authors = {}
    profiles = {}
    for entry in data["entries"]:
        ce = entry["ce"]
        facility_id = ce["facilityId"]
        if facility_id not in contributors:
            contributors[facility_id] = set()
        profile_id = ce["data"]["profileId"]
        contributors[facility_id].add(profile_id)
        if facility_id not in authors:
            authors[facility_id] = {}

        if profile_id not in profiles:
            profiles[profile_id] = ce["data"]["author"]

        if profile_id not in authors[facility_id]:
            authors[facility_id][profile_id] = {'story': 0, 'video': 0, 'note': 0, 'photo': 0}
        authors[facility_id][profile_id][ce["type"]] += type_limit_map[ce["type"]] > \
                                                        authors[facility_id][profile_id][ce["type"]]
        if reacts_to_ours <= 15 and ce["type"] != 'note':
            reacts_to_ours += 1
            # react_to_post(ce["id"])
        name = ce["data"]["facilityName"]
        facility_names[facility_id] = name + " - " + ce["data"]["facilityProvince"]
        points[facility_id] += type_point_map[ce["type"]]
        cer = entry["cer"]
        reaction_counts = 0
        reaction_counts += cer["like"]
        reaction_counts += cer["love"]
        reaction_counts += cer["laugh"]
        reaction_counts += cer["sad"]
        reaction_counts += cer["wow"]
        points[facility_id] += reaction_counts
        reactions[facility_id] += reaction_counts

    for facility_id, author_data in authors.items():
        for author, _data in author_data.items():
            stories[facility_id] += _data['story']
            videos[facility_id] += _data['video']
            notes[facility_id] += _data['note']
            photos[facility_id] += _data['photo']

    return stories, videos, photos, notes, reactions, points, contributors, facility_names, authors, profiles, data[
        "total"]


def produce_report(stories, videos, photos, notes, reactions, points, contributors, facility_names):
    points = dict(sorted(points.items(), key=lambda item: item[1], reverse=True))
    # for facility_id, count in points.items():
    #     pos = list(points.keys()).index(facility_id) + 1
    # print(f"{pos} - {facility_names[facility_id]}: {count}")

    # copy existing report file to a backup
    with open(SAVE_DIR + "kraft.csv", "r") as f:
        with open(SAVE_DIR + "kraft_prev.csv", "w") as f2:
            f2.write(f.read())

    #     save the report as a csv
    with open(SAVE_DIR + "kraft.csv", "w") as f:
        f.write("Facility, stories, videos, photos, notes, reactions, contributors, points\n")
        for facility_id, point in points.items():
            arena = facility_names[facility_id].replace(',', '')
            if 'Trout Creek' in arena:
                save_last_modified_date(stories=stories[facility_id], photos=photos[facility_id],
                                         notes=notes[facility_id], reactions=reactions[facility_id],
                                         contributors=len(contributors[facility_id]))
            f.write(f"{arena}"
                    f",{stories[facility_id]},{videos[facility_id]},{photos[facility_id]},{notes[facility_id]},{reactions[facility_id]},{len(contributors[facility_id])},{points[facility_id]}\n")


def get_story_icon(n):
    # return n
    if n >= 1:
        return "✅"
    return "❌"


def get_photo_icon(n):
    # return n
    if n >= 5:
        return f'{n}✅'
    if n > 0:
        return f'{n}⚠️'
    return "❌"


def get_firstname(name):
    return name.replace(',', '')
    # return name.split(' ')[0]


def get_author_points(counts):
    total = ((counts['story'] * type_point_map['story']) + (counts['video'] * type_point_map['story']) + (
            counts['photo'] * type_point_map['photo']) + (counts['note'] * type_point_map['note']))
    if total == 26:
        return f'{total}⭐'
    return total


def save_author_repo_csv(authors, profiles, facility_names):
    save_qualified_csv(authors, profiles, facility_names)
    # sort authors by name
    for facility, data in authors.items():
        authors[facility] = dict(sorted(data.items(), key=lambda item: profiles[item[0]]))

    with open(SAVE_DIR + "authors.csv", "w") as f:
        f.write("ID, Author, Story, Note, Photo, Points\n")
        for facility, data in authors.items():
            if 'Trout Creek' not in facility_names[facility]:
                continue
            for author, counts in data.items():
                # if 'Trout Creek' in facility_names[facility].replace(',', ''):
                f.write(
                    f"{author},{get_firstname(profiles[author])},{get_story_icon(counts['story'] + counts['video'])},{get_story_icon(counts['note'])},{get_photo_icon(counts['photo'])},{get_author_points(counts)}\n")


def save_qualified_csv(authors, profiles, facility_names):
    # sort authors by name
    for facility, data in authors.items():
        authors[facility] = dict(sorted(data.items(), key=lambda item: profiles[item[0]]))

    with open(SAVE_DIR + "qualified.csv", "w") as f:
        f.write("ID, Author, Story, Note, Photo, Points\n")
        for facility, data in authors.items():
            if 'Trout Creek' not in facility_names[facility]:
                continue
            for author, counts in data.items():
                if str(get_author_points(counts)).count('⭐') != 1:
                    continue
                # if 'Trout Creek' in facility_names[facility].replace(',', ''):
                f.write(
                    f"{author},{get_firstname(profiles[author])},{get_story_icon(counts['story'] + counts['video'])},{get_story_icon(counts['note'])},{get_photo_icon(counts['photo'])},{get_author_points(counts)}\n")


def produce_delta_report(old_csv, new_csv):
    with open(SAVE_DIR + old_csv, "r") as f:
        old = f.readlines()
    with open(SAVE_DIR + new_csv, "r") as f:
        new = f.readlines()
    # get header as keys
    keys = ['Facility', 'stories', 'videos', 'photos', 'notes', 'reactions', 'contributors', 'points']
    old_data = {}
    new_data = {}
    for line in old:
        parts = line.split(',')
        old_data[parts[0]] = parts[1:]
    for line in new:
        parts = line.split(',')
        new_data[parts[0]] = parts[1:]
    top_facilities = 4
    for facility, data in old_data.items():
        if top_facilities == 0:
            break
        top_facilities -= 1
        if facility not in new_data:
            print(f"{facility} has been removed")
            continue
        new_parts = new_data[facility]
        for i, part in enumerate(data):
            old_value = part.replace('\n', '')
            new_value = new_parts[i].replace('\n', '')
            if old_value != new_value:
                # TODO: only update time if changes
                key = keys[i + 1].replace('\n', '')
                print(f"{facility} has changed in {key} + {int(new_value) - int(old_value)}")
    print("Updated at: ", time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))


def save_data_as_csv(data, filename):
    with open(SAVE_DIR + filename, "w") as f:
        for entry in data["entries"]:
            ce = entry["ce"]
            facility_name = ce["data"]["facilityName"].replace(',', '')
            # formatted dd/mm/yyyy
            created_at = ce["created_at"].split('T')[0].replace('-', '/')
            item_type = ce["type"]

            raw_points = type_point_map[item_type]
            cer = entry["cer"]
            points = raw_points
            points += cer["like"]
            points += cer["love"]
            points += cer["laugh"]
            points += cer["sad"]
            points += cer["wow"]
            f.write(f"{created_at},{facility_name},{item_type},{raw_points},{points}\n")


def save_running_total_by_arena_csv(data, filename):
    # sort data by date
    data["entries"].sort(key=lambda x: x["ce"]["created_at"])
    with open(SAVE_DIR + filename, "w") as f:
        f.write("Date, Arena, Type, Raw Points, Points\n")
        points = Counter()
        raw_points = Counter()
        for entry in data["entries"]:
            ce = entry["ce"]
            facility_name = ce["data"]["facilityName"].replace(',', '')
            # formatted dd/mm/yyyy
            created_at = ce["created_at"].split('T')[0].replace('-', '/')
            item_type = ce["type"]
            raw_points[facility_name] += type_point_map[item_type]

            cer = entry["cer"]
            points[facility_name] += type_point_map[item_type]
            points[facility_name] += cer["like"]
            points[facility_name] += cer["love"]
            points[facility_name] += cer["laugh"]
            points[facility_name] += cer["sad"]
            points[facility_name] += cer["wow"]

            f.write(f"{created_at},{facility_name},{item_type},{raw_points[facility_name]},{points[facility_name]}\n")


def job(cookie):
    save_facilities_as_csv(get_facilities(cookie), "kraft_facilities.csv")
    data = fetch_hockeyville_data(cookie)
    stories, videos, photos, notes, reactions, points, contributors, facility_names, authors, profiles, total = get_points_per_facility(
        data)
    produce_report(stories, videos, photos, notes, reactions, points, contributors, facility_names)
    save_author_repo_csv(authors, profiles, facility_names)
    save_data_as_csv(data, "kraft_by_date.csv")
    produce_delta_report("kraft_prev.csv", "kraft.csv")
    save_running_total_by_arena_csv(data, "kraft_running_total.csv")
    print("Total: ", total)
    save_last_modified_date(diff=check_if_git_diff())
    commit_and_push_to_git()


def save_facilities_as_csv(data, filename):
    # sort data by points and treat null points as 0
    data["facilities"].sort(key=lambda x: x['points'] if x['points'] else 0, reverse=True)
    with open(SAVE_DIR + filename, "w") as f:
        f.write("Pos, Facility ID, Facility Name, Lat, Lng, Points\n")
        for facility in data["facilities"]:
            pos = data["facilities"].index(facility) + 1
            points = facility['points'] if facility['points'] else 0
            if 'Trout Creek' in facility['data']['name']:
                save_last_modified_date(pos = pos, points = points)
            f.write(
                f"{pos}, {facility['data']['id']},{facility['data']['name'].replace(',', '')},{facility['data']['lat']},{facility['data']['lng']},{points}\n")


def get_facilities(cookie):
    url = "https://hockeyville.kraftheinz.com/api/facilities"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
        "Cookie": cookie
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    try:
        return response.json()
    except requests.exceptions.JSONDecodeError:
        print(response.content)
        raise ValueError("Response content is not valid JSON or is empty")


def ordinal(n: int):
    if 11 <= (n % 100) <= 13:
        suffix = 'th'
    else:
        suffix = ['th', 'st', 'nd', 'rd', 'th'][min(n % 10, 4)]
    return str(n) + suffix


def save_last_modified_date(pos=None, points=None, stories=None, photos=None, notes=None, reactions=None, contributors=None, diff=False):
    try:
        with open(SAVE_DIR + "meta.json", "r") as f:
            meta = json.load(f)
    except FileNotFoundError:
        meta = {}

    if diff: meta["last_modified"] = time.strftime("%Y-%m-%d %H:%M", time.localtime())
    if pos: meta["pos"] = ordinal(pos)
    if points:
        meta["change_points"] = points - meta["points"]
        meta["points"] = points
    if stories:
        meta["change_stories"] = stories - meta["stories"]
        meta["stories"] = stories
    if photos:
        meta["change_photos"] = photos - meta["photos"]
        meta["photos"] = photos
    if notes:
        meta["change_notes"] = notes - meta["notes"]
        meta["notes"] = notes
    if reactions:
        meta["change_reactions"] = reactions - meta["reactions"]
        meta["reactions"] = reactions
    if contributors:
        meta["change_contributors"] = contributors - meta["contributors"]
        meta["contributors"] = contributors


    with open(SAVE_DIR + "meta.json", "w") as f:
        json.dump(meta, f)


def check_if_git_diff():
    import os
    # --quiet returns exit code 1 if there are changes, 0 if none
    return os.system("git diff --quiet") != 0


def main():
    cookie = input("Enter the cookie: ")
    while True:
        try:
            job(cookie)
        except ValueError:
            cookie = input("Enter the cookie: ")
            job(cookie)
        for _ in tqdm(range(10 * 60), desc="Waiting for next run"):
            time.sleep(1)


def commit_and_push_to_git():
    import os
    print("Committing and pushing to git")
    os.system("git add .")
    os.system("git commit -m 'update'")
    os.system("git push")


if __name__ == "__main__":
    # schedule run every 2 minutes
    main()

# 11efd5fdb2f8b2a06277328bfa6019be
