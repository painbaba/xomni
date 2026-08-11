#!/usr/bin/env python3
"""
yt_upload.py — upload a Shorts-ready MP4 to the user's YouTube channel via Data API v3.

Setup (one time):
  1. Google Cloud Console -> create project -> enable "YouTube Data API v3"
  2. OAuth consent screen (External, add yourself as test user)
  3. Credentials -> OAuth client ID -> type "Desktop app" -> download JSON -> save as
     C:\\Users\\HP\\clipper\\client_secret.json
  4. Run:  python yt_upload.py <clip.mp4> "Title"   (first run opens browser for consent)

Usage:
  python yt_upload.py clip.mp4 "This is my Shorts title #shorts"
  python yt_upload.py clip.mp4 --dry-run          # validate auth without uploading
"""
import argparse, json, os, sys

WORKDIR = os.path.join(os.path.expanduser('~'), 'clipper')
SECRET = os.path.join(WORKDIR, 'client_secret.json')
TOKEN = os.path.join(WORKDIR, 'token.json')
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

def get_authed_service(force_login=False):
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds = None
    if os.path.exists(TOKEN) and not force_login:
        creds = Credentials.from_authorized_user_file(TOKEN, SCOPES)
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(SECRET, SCOPES)
        creds = flow.run_local_server(port=0, prompt='consent')
        with open(TOKEN, 'w') as f:
            f.write(creds.to_json())
        print(f'  token saved to {TOKEN}')
    return build('youtube', 'v3', credentials=creds)

def upload(service, path, title, desc='', tags=None, privacy='public'):
    body = {
        'snippet': {
            'title': title[:100],
            'description': desc[:4900],
            'tags': (tags or ['shorts'])[:500],
            'categoryId': '22',  # People & Blogs
        },
        'status': {'privacyStatus': privacy, 'selfDeclaredMadeForKids': False},
    }
    from googleapiclient.http import MediaFileUpload
    media = MediaFileUpload(path, chunksize=64 * 1024 * 1024, resumable=True)
    req = service.videos().insert(part='snippet,status', body=body, media_body=media)
    vid = None
    while True:
        status, resp = req.next_chunk()
        if resp:
            vid = resp['id']
            print(f'  uploaded: https://youtu.be/{vid}  ({resp["snippet"]["title"][:50]})')
            break
    return vid

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('video')
    ap.add_argument('title', nargs='?', default=None)
    ap.add_argument('--desc', default='')
    ap.add_argument('--tags', default='shorts,viral')
    ap.add_argument('--privacy', default='public', choices=['public', 'unlisted', 'private'])
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--relogin', action='store_true')
    args = ap.parse_args()

    if not os.path.exists(SECRET):
        print(f'ERROR: missing {SECRET}')
        print('Create it: console.cloud.google.com -> project -> enable YouTube Data API v3 ->')
        print('OAuth consent screen -> Credentials -> OAuth client ID (Desktop app) -> download JSON')
        sys.exit(1)

    print('[auth] connecting...')
    svc = get_authed_service(force_login=args.relogin)
    if args.dry_run:
        ch = svc.channels().list(part='snippet', mine=True).execute()
        name = ch['items'][0]['snippet']['title']
        print(f'  auth OK — channel: {name}')
        return
    if not args.title:
        print('ERROR: title required for real upload (or use --dry-run)')
        sys.exit(1)
    print(f'[upload] {os.path.basename(args.video)} -> {args.title}')
    vid = upload(svc, args.video, args.title, args.desc, args.tags.split(','), args.privacy)
    print(f'DONE: https://youtu.be/{vid}')

if __name__ == '__main__':
    main()
