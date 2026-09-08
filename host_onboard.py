# pip install google-api-python-client google-auth requests python-dotenv
import csv
import json
import time
from datetime import datetime
from pathlib import Path
import os
import requests
from dotenv import load_dotenv

from google.oauth2 import service_account
from googleapiclient.discovery import build

# Load secrets from .env (never commit this file)
load_dotenv()

### CONFIG
KEY_PATH = "wauv-503115-7449399e56c3.json"
SPREADSHEET_ID = "1AGvFOBRIquTPXWTbrjvzD-OaxFUDFkozYTc9cu27Jbg"
TAB = "Form Responses 1"
LAST_COL = "G"
STATUS_COL = "H"
SHARED_DRIVE_ID = "0APK2NlDvWvg3Uk9PVA"
TEAM_CALENDAR_ID = "0cafdbcb5af750c64957bc0f2b8d5307290e2a6a13fbbc89baa40873d199bbf9@group.calendar.google.com"

MECH_CSV = Path("mechanical_emails.csv")

GITHUB_ORG = "Wisconsin-AUV"
GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]

POLL_SECONDS = 30

STATE_FILE = Path("state.json")
OUT_DIR = Path("entries")

FIELDS = ["timestamp", "name", "major", "subteam",
          "why_interested", "project_interests", "email"]

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/calendar"
]

creds = service_account.Credentials.from_service_account_file(KEY_PATH, scopes=SCOPES)

# build the clients for the APIs
sheets = build("sheets", "v4", credentials=creds).spreadsheets()
drive = build("drive", "v3", credentials=creds)
calendar = build("calendar", "v3", credentials=creds)

def add_to_github_org(email: str, role: str = "direct_member"):
    """Invite one person to the GitHub org by email"""
    resp = requests.post(
        f"https://api.github.com/orgs/{GITHUB_ORG}/invitations",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        json={"email": email, "role": role},
    )
    if resp.status_code == 201:
        print(f"Invited to GitHub: {email}")
    elif resp.status_code == 422:
        print(f"GitHub skip ({email}): {resp.json().get('message', resp.text[:200])}")
    else:
        print(f"GitHub invite FAILED ({resp.status_code}): {resp.text[:200]}")
    return resp

def add_to_calendar(email: str, role: str = "reader"):
    """Share the team calendar with one person (they get an email to add it)."""
    calendar.acl().insert(
        calendarId=TEAM_CALENDAR_ID,
        body={"role": role, "scope": {"type": "user", "value": email}},
        sendNotifications=True,
    ).execute()

def save_email(email: str):
    """Append a Mechanical member's email to the CSV."""
    new = not MECH_CSV.exists()
    with MECH_CSV.open("a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["email"])
        w.writerow([email])

def read_cursor():
    """Last handled row. 1 = header only, so start at row 2."""
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())["last_row"]
    return 1

def write_cursor(row: int):
    """Write the current last row to a log file."""
    STATE_FILE.write_text(json.dumps({"last_row": row}))

def handle(entry: dict, row: int):
    """Process each entry."""
    print(f"[row {row}] {entry['name']} <{entry['email']}> -> {entry['subteam']}")

    try:
        # Add every member to the Google Drive
        drive.permissions().create(
            fileId=SHARED_DRIVE_ID,
            body={
                "type": "user",
                "role": "writer",
                "emailAddress": entry["email"],
            },
            sendNotificationEmail=True,
            supportsAllDrives=True,
        ).execute()

        # Add every member to the team calendar
        add_to_calendar(entry["email"])

        subteams = [team.strip() for team in entry["subteam"].split(",")]

        if "Mechanical" in subteams:
            # Save email to CSV because OnShape requires admin action to add
            save_email(entry["email"])

        if "Electrical" in subteams:
            print("EEE")

        if "Software" in subteams:
            add_to_github_org(entry["email"])

        if "Business" in subteams:
            print("Boo")

    except Exception as e:
        print("When adding ", entry['name'], " : ", e)

    OUT_DIR.mkdir(exist_ok=True)
    (OUT_DIR / f"{row:04d}.json").write_text(json.dumps(entry, indent=2))

def poll(cursor: int):
    """Handle everything below the cursor, mark it, then return the new cursor."""
    rows = sheets.values().get(
    spreadsheetId=SPREADSHEET_ID,
    range=f"'{TAB}'!A{cursor + 1}:{LAST_COL}",
    ).execute().get("values", [])

    if not rows:
        return cursor

    for i, row in enumerate(rows):
        padded = row + [""] * (len(FIELDS) - len(row))
        handle(dict(zip(FIELDS, padded)), cursor + 1 + i)

    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    sheets.values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=f"'{TAB}'!{STATUS_COL}{cursor + 1}",
        valueInputOption="RAW",
        body={"values": [[stamp] for _ in rows]},
    ).execute()

    # update the cursos
    cursor += len(rows)
    write_cursor(cursor)

    return cursor

def main():
    cursor = read_cursor()

    print(f"watching '{TAB}' from row {cursor + 1}, every {POLL_SECONDS}s")

    while True:
        try:
            cursor = poll(cursor)
        except KeyboardInterrupt:
            return print("\nstopped")
        except Exception as e:
            print(f"error, retrying: {e!r}")
        time.sleep(POLL_SECONDS)

if __name__ == "__main__":
    main()