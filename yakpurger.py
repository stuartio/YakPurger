import argparse
import m3u8
import requests
import os
from urllib.parse import urlsplit


def get_playlist(playlist_uri):
    response = requests.get(playlist_uri)
    response.raise_for_status()
    playlist = m3u8.loads(response.text)
    urlpath = urlsplit(playlist_uri).path
    filename = os.path.basename(urlpath)
    playlist.base_uri = playlist_uri.replace(filename, "")
    return playlist


def parse_playlist(playlist):
    segments = set()
    if hasattr(playlist, "segments"):
        for segment in playlist.segments:
            segment_uri = playlist.base_uri + segment.uri
            segments.add(segment_uri)

    if hasattr(playlist, "playlists"):
        # Use set to dedupe playlist list
        child_playlist_uris = set()
        for child_playlist_path in playlist.playlists:
            child_playlist_uris.add(playlist.base_uri + child_playlist_path.uri)

        for child_playlist_uri in child_playlist_uris:
            child_playlist = get_playlist(child_playlist_uri)
            child_segments = parse_playlist(child_playlist)
            segments.update(child_segments)

    return segments


# Set options
usage = "usage: python yakpurger.py (--url https://example.com/master.m3u8 | --file list_of_urls.txt) [--edgerc ~/.edgerc] [--section default] [--accountSwitchKey <ask>] [--debug]"
parser = argparse.ArgumentParser(usage=usage)
parser_group = parser.add_mutually_exclusive_group()
parser_group.add_argument(
    "-u", "--url", action="store", dest="url", required=False, help="Playlist URI to retrieve and parse"
)
parser_group.add_argument(
    "-f",
    "--file",
    action="store",
    dest="input_file",
    required=False,
    help="Text file providing list of Playlist URIs to parse",
)
parser.add_argument(
    "-d", "--debug", action="store_true", dest="debug", default="False", help="Add verbose debug logging"
)
parser.add_argument("-e", "--edgerc", action="store", dest="edgerc", help='EdgeRC file. Defaults to "~/.edgerc"')
parser.add_argument("-s", "--section", action="store", dest="section", help='EdgeRC Section. Defaults to "default"')
parser.add_argument(
    "-a",
    "--accountSwitchKey",
    action="store",
    dest="accountSwitchKey",
    help="Account switch key. Only used by Akamai internal staff",
)

args = parser.parse_args()

# Set array to collate segment urls
all_segments = set()

# Collate file list
if args.url is not None:
    playlist_uris = [args.url]
else:
    with open(args.input_file) as f:
        playlist_uris = f.read()
        playlist_uris = playlist_uris.split("\n")

# Iterate through files
for playlist_uri in playlist_uris:
    print(f"Parsing playlist: {playlist_uri}")
    playlist = get_playlist(playlist_uri)
    playlist_segments = parse_playlist(playlist)
    print(f"Found {len(playlist_segments)} segments")
    all_segments.update(playlist_segments)

all_segments = sorted(all_segments)
with open("output.txt", "w") as o:
    o.write("\n".join(all_segments))

print(f"Segment count = {len(all_segments)}")
print("process complete")
