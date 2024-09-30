import argparse
import m3u8
import requests
import os
import sys
from urllib.parse import urlsplit
from ak.purge import Purge
from colorama import Fore
from urllib.parse import urlparse
import time
import datetime
import json


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

    if args.log_file:
        log_entry = str(datetime.datetime.now()) + " -- " + context + " -- " + message + "\n"
        with open(args.log_file, "a", encoding="utf8") as log_fp:
            log_fp.write(log_entry)


def get_playlist(playlist_uri):
    try:
        response = requests.get(playlist_uri)
        response.raise_for_status()
    except:
        report(playlist_uri, "Initial request failed. Retrying...")
        try:
            response = requests.get(playlist_uri)
            response.raise_for_status()
        except Exception:
            raise f"{playlist_uri}: Failed to retrieve twice. The purge collection for this asset will likely be incomplete"
    playlist = m3u8.loads(response.text)
    parsed_url = urlparse(playlist_uri)
    urlpath = parsed_url.path
    filename = os.path.basename(urlpath)

    # Extract URL without query
    url_without_query = playlist_uri
    if parsed_url.query != "":
        url_without_query = url_without_query.replace(f"?{parsed_url.query}", "")

    playlist.base_uri = url_without_query.replace(filename, "")
    playlist.uri = playlist_uri
    return playlist


def parse_playlist(playlist, exclude_segments):
    segment_extensions = ["mp4", "ts", "mp4a", "mp4v"]
    purge_urls = set()
    purge_urls.add(playlist.uri)

    if hasattr(playlist, "segments"):
        for file in playlist.segments:
            file_uri = playlist.base_uri + file.uri

            # Exclude segments
            exclude_segment = False
            if exclude_segments:
                for extension in segment_extensions:
                    if file.uri.endswith(extension):
                        exclude_segment = True
            if not exclude_segment:
                purge_urls.add(file_uri)

    if hasattr(playlist, "playlists"):
        # Use set to dedupe playlist list
        child_playlist_uris = set()
        for child_playlist_path in playlist.playlists:
            child_playlist_uri = playlist.base_uri + child_playlist_path.uri
            child_playlist_uris.add(child_playlist_uri)
            purge_urls.add(child_playlist_uri)

        for child_playlist_uri in child_playlist_uris:
            child_playlist = get_playlist(child_playlist_uri)
            child_segments = parse_playlist(child_playlist, exclude_segments)
            purge_urls.update(child_segments)

    if hasattr(playlist, "media"):
        # Use set to dedupe playlist list
        media_playlist_uris = set()
        for media_playlist_path in playlist.media:
            media_playlist_uri = playlist.base_uri + media_playlist_path.uri
            media_playlist_uris.add(media_playlist_uri)
            purge_urls.add(media_playlist_uri)

        for media_playlist_uri in media_playlist_uris:
            media_playlist = get_playlist(media_playlist_uri)
            media_segments = parse_playlist(media_playlist, exclude_segments)
            purge_urls.update(media_segments)

    return purge_urls


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
    "-b",
    "--batchSize",
    action="store",
    dest="batch_size",
    default=250,
    help="Number of URLs to purge in a single request. Defaults to 250, but this may need to be lower for longer URLs.",
    type=int,
)
parser.add_argument(
    "-n",
    "--network",
    action="store",
    dest="network",
    default="production",
    help="Network to purge assets from. Only 'production' or 'staging' are accepted. Defaults to 'production'.",
    choices=["production", "staging"],
)
parser.add_argument(
    "-m",
    "--purgeMethod",
    action="store",
    dest="method",
    default="delete",
    help="Method of purging to perform. Only 'invalidate' or 'delete' are accepted. Defaults to 'delete'.",
    choices=["invalidate", "delete"],
)
parser.add_argument(
    "--excludeSegments",
    action="store_true",
    dest="exclude_segments",
    help="Do not purge segment files. All other referenced files will be purged.",
)
parser.add_argument(
    "-p",
    "--prefix",
    action="store",
    dest="prefix",
    help="Prefix to be added to all manifest URLs, e.g. --prefix 'https://streaming.com/token' .",
)
parser.add_argument(
    "-l",
    "--logFile",
    action="store",
    dest="log_file",
    help="Log output to file.",
)
parser.add_argument("-d", "--debug", action="store_true", dest="debug", default=False, help="Add verbose debug logging")
parser.add_argument("-e", "--edgerc", action="store", dest="edgerc", help='EdgeRC file. Defaults to "~/.edgerc"')
parser.add_argument("-s", "--section", action="store", dest="section", help='EdgeRC Section. Defaults to "default"')

global args
args = parser.parse_args()
report("Global", "ARGS: " + str(vars(args)), level="debug")

start = time.time()

# Configure purge client
purge_client = Purge(args.edgerc, args.section)

# defaults
PURGE_BATCH_SIZE = args.batch_size

# Set array to collate segment urls
all_files = set()

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
        if args.prefix:
            playlist_uri = args.prefix + playlist_uri

        report("Parsing", f"Parsing playlist uri: '{playlist_uri}'", level="debug")

        parsed_playlist = urlparse(playlist_uri)
        playlist_file = parsed_playlist.path[parsed_playlist.path.rfind("/") + 1 :]
        report(playlist_file, "Parsing playlist")
        try:
            playlist = get_playlist(playlist_uri)
        except Exception as err:
            report(playlist_file, "An error has occurred. Skipping to next manifest", level="error")
            report(playlist_file, err, level="error")
            continue
        playlist_files = parse_playlist(playlist, args.exclude_segments)
        report(playlist_file, f"Found {len(playlist_files)} files")
        all_files.update(playlist_files)

all_files = sorted(all_files)
report("Discovery", f"-- Found {len(all_files)} files to purge")

total_batches = (len(all_files) // PURGE_BATCH_SIZE) + 1
report("Discovery", f"-- Segments divided into {total_batches} batches")

## Write all_files to temp file
with open("output.txt", "w") as o:
    o.write("\n".join(all_files))

for batch in range(total_batches):
    # Skip this iteration if skipToBatch provided
    if args.skip_to_batch and args.skip_to_batch > batch:
        continue

    start_range = 0 + (batch * PURGE_BATCH_SIZE)
    end_range = (start_range + PURGE_BATCH_SIZE) - 1
    if end_range > len(all_files):
        end_range = len(all_files)
    report(f"Batch {batch}", f"Purging batch {batch}. Range = {start_range}-{end_range}, method = {args.method}")

    try:
        purge_objects = all_files[start_range:end_range]
        if args.method == "delete":
            purge_result = purge_client.deleteByUrl(network=args.network, objects=purge_objects)
        else:
            purge_result = purge_client.invalidateByUrl(network=args.network, objects=purge_objects)
        if args.log_file:
            log_time = str(datetime.datetime.now())
            log_message = log_time + " -- " + f"Purging {PURGE_BATCH_SIZE} urls with method {args.method}\n"
            with open(args.log_file, "a", encoding="utf8") as log_fp:
                log_fp.write(log_message)
                for purge_object in purge_objects:
                    log_fp.write(f"{log_time} -- {purge_object}\n")

    except Exception as err:
        report(
            f"Batch {batch}",
            f"An error occurred in purging. Please re-run the script with the '--skipToBatch {batch}'",
            level="error",
        )
        report(f"Batch {batch}", str(err), level="error")
        sys.exit(1)

runtime = time.time() - start
report("Global", f"Process complete in {runtime}s")
