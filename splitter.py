import re
import argparse
from requests import get

version = "0.0.1 - In development"
args = parseArgs()

def main():
    processArgs(args)

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
        "url": "Gets description from URL (unnecessary with --download)",
        "download": "Downloads video from youtube (requires youtube-dl)",
        "args": "Args to pass to youtube-dl (only with --download)(make sure to put between quotes)",
        "keep": "Keep original video",
        "regex-name": "Specify custom regex for file name",
        "regex-timestamp": "Specify custom regex for timestamp",
        "debug": "Start in debug mode. Prints text to follow program's flow."
    }

    videoDestination = parser.add_mutually_exclusive_group()
    timestampDestination = parser.add_mutually_exclusive_group()

    parser.add_argument("--version",
                        action="store_true",
                        dest="version",
                        help=help_texts["version"])

    timestampDestination.add_argument("-f", "--file",
                        action="store",
                        dest="file",
                        help=help_texts["file"])

    videoDestination.add_argument("-v",
                        action="store",
                        dest="video",
                        help=help_texts["video"])

    parser.add_argument("-n", "--numerical",
                        action="store_true",
                        dest="numerical",
                        help=help_texts["numerical"])

    timestampDestination.add_argument("-u", "--url",
                        action="store",
                        dest="url",
                        help=help_texts["url"])

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
                        dest="regex-name",
                        help=help_texts["regex-name"])

    parser.add_argument("--regex-timestamp",
                        action="store",
                        dest="regex-timestamp",
                        default="^\d{1,2}:\d{2}:*\d{0,2}",
                        help=help_texts["regex-timestamp"])

    parser.add_argument("-d", "--debug",
                        action="store_true",
                        dest="debug",
                        help=help_texts["debug"])

    return parser.parse_args()

if __name__ == "__main__":
    main()
