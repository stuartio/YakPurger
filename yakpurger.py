import argparse
import m3u8
import requests
import os
import sys
from urllib.parse import urlsplit
from ak.purge import Purge
from colorama import Fore
from urllib.parse import urlparse


def report(context, message, level="info"):
    if level == "debug":
        if args.debug == True:
            print(Fore.CYAN + context + ": ", end="")
            print(Fore.YELLOW + "[DEBUG] " + message)
    elif level == "warning":
        print(Fore.CYAN + context + ": ", end="")
        print(Fore.YELLOW + "[WARNING] " + message + Fore.WHITE)
    elif level == "error":
        print(Fore.CYAN + context + ": ", end="")
        print(Fore.RED + "[ERROR] " + message + Fore.WHITE)
    else:
        print(Fore.CYAN + context + ": ", end="")
        print(Fore.WHITE + message)


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
    "--skipToBatch",
    action="store",
    dest="skip_to_batch",
    help="When retrying after an error you can use this option to skip to the problematic batch and avoid retrying all the batches which ran successfully previously",
    type=int,
)
parser.add_argument(
    "-d", "--debug", action="store_true", dest="debug", default="False", help="Add verbose debug logging"
)
parser.add_argument("-e", "--edgerc", action="store", dest="edgerc", help='EdgeRC file. Defaults to "~/.edgerc"')
parser.add_argument("-s", "--section", action="store", dest="section", help='EdgeRC Section. Defaults to "default"')

args = parser.parse_args()

# Configure purge client
purge_client = Purge(args.edgerc, args.section)

# defaults
PURGE_BATCH_SIZE = 200

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
    if playlist_uri != "":
        parsed_playlist = urlparse(playlist_uri)
        playlist_file = parsed_playlist.path[parsed_playlist.path.rfind("/") + 1 :]
        report(playlist_file, "Parsing playlist")
        playlist = get_playlist(playlist_uri)
        playlist_segments = parse_playlist(playlist)
        report(playlist_file, f"Found {len(playlist_segments)} segments")
        all_segments.update(playlist_segments)

all_segments = sorted(all_segments)
report("Discovery", f"-- Found {len(all_segments)} segments to process")

total_batches = len(all_segments) // PURGE_BATCH_SIZE
report("Discovery", f"-- Segments divided into {total_batches} batches")

for batch in range(total_batches):
    # Skip this iteration if skipToBatch provided
    if args.skip_to_batch and args.skip_to_batch > batch:
        continue

    start_range = 0 + (batch * PURGE_BATCH_SIZE)
    end_range = (start_range + PURGE_BATCH_SIZE) - 1
    report(f"Batch {batch}", f"Purging batch {batch}. Range = {start_range}-{end_range}")

    try:
        purge_objects = all_segments[start_range:end_range]
        purge_result = purge_client.invalidateByUrl(network="staging", objects=purge_objects)
    except Exception as err:
        report(
            f"Batch {batch}",
            f"An error occurred in purging. Please re-run the script with the '--skipToBatch {batch}'",
            level="error",
        )
        report(f"Batch {batch}", str(err), level="error")
        sys.exit(1)

print("process complete")
