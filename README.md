# YakPurger

This tool will take in a list of HLS manifest URLs, retrieve the content, parse for segments, then purge the segments in batches.

## Requirements

You can install all required pips by running the following:

```shell
python -m pip install -r requirements.txt
```

## Credentials

As the purge API does not support account switching, you will need credentials in the form of a .edgerc file from the account you wish to purge. Alternatively you can use environment variables in the form `AKAMAI_HOST`, `AKAMAI_CLIENT_TOKEN` etc., or if you combine with a `--section` parameter you can use `AKAMAI_<SECTION>_HOST`, `AKAMAI_<SECTION>_CLIENT_TOKEN`, and so on.

## Usage

```shell
usage: usage: python yakpurger.py (--url https://example.com/master.m3u8 | --file list_of_urls.txt) [--edgerc ~/.edgerc] [--section default] [--accountSwitchKey <ask>] [--debug]

options:
  -h, --help            show this help message and exit
  -u URL, --url URL     Playlist URI to retrieve and parse
  -f INPUT_FILE, --file INPUT_FILE
                        Text file providing list of Playlist URIs to parse
  --skipToBatch SKIP_TO_BATCH
                        When retrying after an error you can use this option to skip to the problematic batch and avoid retrying all the batches which ran successfully
                        previously
  -b BATCH_SIZE, --batchSize BATCH_SIZE
                        Number of URLs to purge in a single request. Defaults to 250, but this may need to be lower for longer URLs.
  -n {production,staging}, --network {production,staging}
                        Network to purge assets from. Only 'production' or 'staging' are accepted. Defaults to 'production'.
  -m {invalidate,delete}, --purgeMethod {invalidate,delete}
                        Method of purging to perform. Only 'invalidate' or 'delete' are accepted. Defaults to 'delete'.
  --excludeSegments     Do not purge segment files. All other referenced files will be purged.
  -p PREFIX, --prefix PREFIX
                        Prefix to be added to all manifest URLs, e.g. --prefix 'https://streaming.com/token' .
  -l LOG_FILE, --logFile LOG_FILE
                        Log output to file.
  -d, --debug           Add verbose debug logging
  -e EDGERC, --edgerc EDGERC
                        EdgeRC file. Defaults to "~/.edgerc"
  -s SECTION, --section SECTION
                        EdgeRC Section. Defaults to "default"
```

The script works in one of two ways: url mode or file mode. In url mode you present a url in the command line, and a single playlists is retrieved and parsed. In file mode you can point the script to a txt file where each line is a playlist. The files from all playlists are aggregated then purged in batches.

## Examples

1. Purge all files referenced in mymanifests.txt

```shell
python yakpurger.py -f mymanifests.txt --edgerc yakpurger.edgerc
```

2. Purge all files referenced in mymanifests.txt, exclude segment files

```shell
python yakpurger.py -f mymanifests.txt --edgerc yakpurger.edgerc --excludeSegments
```

3. Purge all files referenced in mymanifests.txt on the staging network

```shell
python yakpurger.py -f mymanifests.txt --edgerc yakpurger.edgerc --network staging
```

4. Purge all files referenced in mymanifests.txt on the staging network using the invalidate method

```shell
python yakpurger.py -f mymanifests.txt --edgerc yakpurger.edgerc --network staging --purgeMethod invalidate
```

5. Purge all files referenced in mymanifests.txt resume from batch 50

```shell
python yakpurger.py -f mymanifests.txt --edgerc yakpurger.edgerc --skipToBatch 50
```

6. Purge all files referenced in mymanifests.txt, limit batch size to 100 (useful if 250 requests exceeds the purge API POST size)

```shell
python yakpurger.py -f mymanifests.txt --edgerc yakpurger.edgerc --batchSize 100
```

7. Purge all files referenced by URL

```shell
python yakpurger.py -u https://stream.com/master.m3u8 --edgerc yakpurger.edgerc
```

8. Purge all files referenced by file, prepend the same URL to all

```shell
python yakpurger.py -f manifest_paths.txt --prefix https://stream.com/manifests --edgerc yakpurger.edgerc
```

9. Purge all files referenced in mymanifests.txt, log to purge.log

```shell
python yakpurger.py -f mymanifests.txt --edgerc yakpurger.edgerc --logFile purge.log
```