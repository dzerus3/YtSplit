#!/usr/bin/python3

import re
import argparse
import subprocess
from os import remove

version = "0.1.1 - Alpha"

def main():
    timestamps = getTimestamps()
    splitVideo(timestamps)

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
    time = re.search(arguments.regex_timestamp, line)

    # If there is external text
    if not time:
        return [None, None]

    # If there is a timestamp without a name
    name = re.search(arguments.regex_name, line)
    if not name:
        return [time.group(0), None]

    return [time.group(0), name.group(0)]

def splitVideo(timestamps):
    currentTime = getStartingTime(timestamps[0][0])
    segmentNumber = 1

    videoName = downloadVideo()
    fileFormat = getFileFormat(videoName)
    videoDuration = getVideoDuration(videoName)

    for stamp in timestamps:
        if arguments.numerical:
            name = str(segmentNumber)
        else:
            name = stamp[1]

        endTime = getEndTime(segmentNumber, timestamps, videoDuration)
        #TODO make this work
        command = ["ffmpeg", "-ss", currentTime, "-t", endTime, "-i", videoName, "-acodec", "copy", "-vcodec", "copy", "\"" + name + "." + fileFormat + "\""]

        command = f"ffmpeg -ss {currentTime} -to {endTime} -i {videoName} -acodec copy -vcodec copy \"{name}.{fileFormat}\""

        subprocess.call(command, shell=True)

        segmentNumber += 1
        currentTime = endTime

        if not arguments.keep:
            remove(videoName)

# Downloads video if asked for it. If not, just returns video file name.
def downloadVideo():
    if arguments.video:
        return arguments.video
    else:
        downloadCommand = ["youtube-dl", "-o", "ytdl-output.%(ext)s", "-w", "--no-post-overwrites", arguments.download]
        # Most videos merged into mkv by default.
        outputFormat = "mkv"

        if arguments.args: #TODO Test this
            args = " ".join(argument.args)
            downloadCommand += args

        if arguments.format:
            outputFormat = arguments.format
            videoFormat = ["--recode-video", arguments.format]
            downloadCommand += videoFormat
        elif arguments.extract_audio:
            outputFormat = arguments.extract_audio
            audioFormat = ["--extract-audio", "--audio-format", arguments.extract_audio]
            downloadCommand += audioFormat

        subprocess.call(downloadCommand)

        return "ytdl-output." + outputFormat

def getFileFormat(videoName):
    print(videoName)
    fileFormat = re.search("(?<=\.)\w*", videoName)
    if not fileFormat:
        print("Could not find file extension in file name. Quitting.")
        quit()

    return fileFormat.group(0)

def getEndTime(current, timestamps, videoDuration):
    if current == len(timestamps):
        return videoDuration
    else:
        return timestamps[current][0]

def getStartingTime(firstTimestamp):
    if arguments.zero:
        return "0:00"
    else:
        return firstTimestamp

def getVideoDuration(videoName):
    duration = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", "-sexagesimal", videoName]).decode("utf-8")

    return re.sub("'|\n", "", duration)

def parseArgs():
    parser = argparse.ArgumentParser(
        description="YtSplit - Splits a file based on Youtube timestamps.",
        epilog="Note that FFMPEG is required to use this program."
    )

    help_texts = {
        "file": "Destination of file with timestamps",
        "video": "Destination of video file",
        "numerical": "Name videos numerically (useful if file does not follow `timestamp - name` format)",
        "zero": "Start with the first timestamp at 00:00. Useful if the first timestamp is not there.",
        "download": "Downloads video from youtube (requires youtube-dl)",
        "args": "Args to pass to youtube-dl (only with --download and do not use the -o option)",
        "format": "Specify output format for downloaded video (only for download)",
        "extract_audio": "Tell youtube-dl to extract audio from video",
        "keep": "Keep original video",
        "regex_name": "Specify custom regex for file name",
        "regex_timestamp": "Specify custom regex for timestamp"
    }

    videoDestination = parser.add_mutually_exclusive_group(required=True)

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

    parser.add_argument("-0", "--zero",
                        action="store_true",
                        dest="zero",
                        help=help_texts["zero"])

    videoDestination.add_argument("--download",
                        action="store",
                        dest="download",
                        help=help_texts["download"])

    parser.add_argument("-a", "--args",
                        action="store",
                        dest="args",
                        help=help_texts["args"])

    parser.add_argument("--format",
                        action="store",
                        dest="format",
                        help=help_texts["format"])

    parser.add_argument("--extract-audio",
                        action="store",
                        dest="extract_audio",
                        help=help_texts["extract_audio"])

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

    return parser.parse_args()

if __name__ == "__main__":
    arguments = parseArgs()
    main()
