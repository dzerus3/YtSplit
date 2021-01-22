import re
import argparse
import subprocess
from bs4 import BeautifulSoup
from requests import get

version = "0.0.1 - In development"

def main():
    if arguments.version:
        print(version)
        quit()

    timestamps = getTimestamps()
    print(timestamps)

# Returns timestamp in whichever way the user specified.
def getTimestamps():
    timestamps = []
    with open(arguments.file, "r") as timestampFile:
        for line in timestampFile.readlines():
            timestamp = getTimestampFromLine(line)
            if timestamp[0]:
                timestamps.append(timestamp)
    return timestamps

# Runs a regex on specified string to get the corresponding name and timestamp from a line in the description.
def getTimestampFromLine(line):
    time = re.search(str(arguments.regex_timestamp), line)

    # If there is external text
    if not time:
        return [None, None]

    # If there is a timestamp without a name
    name = re.search(str(arguments.regex_name), line)
    if not name:
        return [time.group(0), None]

    return [time.group(0), name.group(0)]

def parseArgs():
    parser = argparse.ArgumentParser(
        description="YtSplit - Splits a file based on Youtube timestamps.",
        epilog="Note that FFMPEG is required to use this program."
    )

    help_texts = {
        "version": "Output program version and exit.",
        "file": "Destination of file with timestamps",
        "video": "Destination of video file",
        "numerical": "Name videos numerically (useful if file does not follow `timestamp - name` format)",
        "download": "Downloads video from youtube (requires youtube-dl)",
        "args": "Args to pass to youtube-dl (only with --download and do not use the -o option)",
        "keep": "Keep original video",
        "regex_name": "Specify custom regex for file name",
        "regex_timestamp": "Specify custom regex for timestamp",
        "debug": "Start in debug mode. Prints text to follow program's flow."
    }

    videoDestination = parser.add_mutually_exclusive_group(required=True)

    parser.add_argument("--version",
                        action="store_true",
                        dest="version",
                        help=help_texts["version"])

    parser.add_argument("-f", "--file",
                        action="store",
                        dest="file",
                        required=True,
                        help=help_texts["file"])

    videoDestination.add_argument("-v",
                        action="store",
                        dest="video",
                        help=help_texts["video"])

    parser.add_argument("-n", "--numerical",
                        action="store_true",
                        dest="numerical",
                        help=help_texts["numerical"])

    videoDestination.add_argument("--download",
                        action="store",
                        dest="download",
                        help=help_texts["download"])

    parser.add_argument("-a", "--args",
                        action="store",
                        dest="args",
                        help=help_texts["args"])

    parser.add_argument("-k", "--keep",
                        action="store",
                        dest="keep",
                        help=help_texts["keep"])

    parser.add_argument("--regex-name",
                        action="store",
                        dest="regex_name",
                        default="(?<=-\ ).*",
                        help=help_texts["regex_name"])

    parser.add_argument("--regex-timestamp",
                        action="store",
                        dest="regex_timestamp",
                        default="^\d{1,2}:\d{2}:*\d{0,2}",
                        help=help_texts["regex_timestamp"])

    parser.add_argument("-d", "--debug",
                        action="store_true",
                        dest="debug",
                        help=help_texts["debug"])

    return parser.parse_args()

if __name__ == "__main__":
    arguments = parseArgs()
    main()
