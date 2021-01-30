#!/usr/bin/python3

import re
import argparse
import subprocess
import youtube_dl
from os import remove
from datetime import timedelta

version = "1.0.0 - Release"

def main():
    timestamps = TimestampRetriever()
    splitter = VideoManipulator(timestamps.getTimestamps())
    splitter.splitVideo()

def dbg_print(output):
    if arguments.debug:
        print(output)

class TimestampRetriever:
# Returns timestamp in whichever way the user specified.
    def getTimestamps(self):
        self.checkTimestampSource()

        if arguments.file:
            timestamps = self.getTimestampFromFile(arguments.file)

        else:
            timestamps = self.getTimestampFromDescription(arguments.url)

        return timestamps

    def checkTimestampSource(self):
        if arguments.file is None and arguments.url is None:
            print('Either a file or a URL with timestamps is required')
            quit()

    def getTimestampFromDescription(self, url):
        dbg_print("Retrieving timestamps from Youtube")
        timestamps = list()
        with youtube_dl.YoutubeDL({}) as ydl:
            infoDict = ydl.extract_info(url, download=False)
            description = infoDict.get("description", None)
            for line in iter(description.splitlines()):
                timestamp = self.getTimestampFromLine(line)
                if timestamp[0]:
                    timestamps.append(timestamp)
        return timestamps

    def getTimestampFromFile(self, fileName):
        dbg_print("Retrieving timestamps from text file")
        timestamps = list()
        with open(arguments.file, "r") as timestampFile:
            for line in timestampFile.readlines():
                timestamp = self.getTimestampFromLine(line)
                if timestamp[0]:
                    timestamps.append(timestamp)

        return timestamps

    def getTimestampFromLine(self, line):
        time = re.search(arguments.regex_timestamp, line)

        # If there is external text
        if not time:
            return [None, None]

        # If there is a timestamp without a name
        name = re.search(arguments.regex_name, line)
        if not name:
            return [time.group(0), None]

        return [time.group(0), name.group(0)]

class VideoDownloader:
    def getVideo(self):
        if arguments.video:
            return arguments.video
        else:
            dbg_print("Downloading video from youtube")
            ydlOpts = self.setDownloadOptions()
            self.downloadVideo(ydlOpts)
            self.checkForWebm()

            return "ytdl-output." + self.outputFormat

    def downloadVideo(self, ydlOpts):
        with youtube_dl.YoutubeDL(ydlOpts) as ydl:
            ydl.download([arguments.url])

    # Downloads video if asked for it. If not, just returns video file name.
    def setDownloadOptions(self):
        #TODO Allow user to use video name as big file name
        ydlOpts = {'outtmpl': 'ytdl-output.%(ext)s'}
        # Most videos are merged into mkv by default.
        #TODO: fails if it merges to webm instead
        self.outputFormat = "mkv"

        if arguments.format:
            dbg_print(f"youtube-dl will reencode video in {arguments.format} format")
            self.outputFormat = arguments.format
            ydlOpts["recodevideo"] = self.outputFormat
        elif arguments.extract_audio:
            dbg_print(f"youtube-dl will extract audio in {arguments.extract_audio} format")
            self.outputFormat = arguments.extract_audio
            ydlOpts["extractaudio"] = True
            ydlOpts["audioformat"] = arguments.extract_audio

        return ydlOpts

    def checkForWebm(self):
        try:
            open("ytdl-output." + self.outputFormat, "r")
        except:
            self.outputFormat = "webm"

class VideoManipulator:
    def __init__(self, timestamps):
        downloader = VideoDownloader()
        self.timestampManip = TimestampManipulator()

        self.timestamps = timestamps
        self.videoName = downloader.getVideo()
        self.fileFormat = self.getFileFormat(self.videoName)

    def splitVideo(self):
        currentTime = self.timestampManip.getStartingTime(self.timestamps[0][0])
        videoDuration = self.getVideoDuration(self.videoName)
        segmentNumber = 1

        dbg_print("Starting to split the file")
        for stamp in self.timestamps:
            name = self.getSegmentName(str(segmentNumber), stamp[1])

            endTime = self.timestampManip.getEndTime(videoDuration, segmentNumber, self.timestamps)

            dbg_print("Timestamp before padding: " + currentTime + "  " + endTime)
            processedStart, processedEnd = self.timestampManip.padTimestamps(currentTime, endTime)
            dbg_print("Timestamp after padding: " + processedStart + "  " + processedEnd)

            #TODO make this work
            # command = ["ffmpeg", "-ss", currentTime, "-t", endTime, "-i", videoName, "-acodec", "copy", "-vcodec", "copy", "\"" + name + "." + fileFormat + "\""]
            # subprocess.call(command)

            command = f"ffmpeg -y -hide_banner -loglevel error -i {self.videoName} -acodec copy -vcodec copy -ss {processedStart} -to {processedEnd} \"{name}.{self.fileFormat}\""
            dbg_print(command)
            subprocess.call(command, shell=True)

            segmentNumber += 1
            currentTime = endTime

        self.removeOriginal()

    # Checks what the segment should be named based on whether -n was passed.
    def getSegmentName(self, numerical, full):
        if arguments.numerical:
            return numerical
        else:
            return full

    # Deletes the split video unless -k was passed
    def removeOriginal(self):
        if not arguments.keep:
            dbg_print("Deleting split video...")
            remove(self.videoName)

    def getFileFormat(self, videoName):
        fileFormat = re.search("(?<=\.)\w*", videoName)
        if not fileFormat:
            print("Could not find file extension in file name. Quitting.")
            quit()

        return fileFormat.group(0)

    def getVideoDuration(self, videoName):
        dbg_print("Running ffprobe to get video duration")
        command = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", "-sexagesimal", videoName]
        duration = subprocess.check_output(command).decode("utf-8")

        return re.sub("'|\n", "", duration)

class TimestampManipulator:
    def getStartingTime(self, firstTimestamp):
        if arguments.zero:
            return "0:00"
        else:
            return firstTimestamp

    def getEndTime(self, videoDuration, segmentNumber, timestamps):
        if segmentNumber == len(timestamps):
            return videoDuration
        else:
            return timestamps[segmentNumber][0]

    def padTimestamps(self, segmentStart, segmentEnd):
        if arguments.pad:
            startSeconds = self.convertToSeconds(segmentStart)
            endSeconds = self.convertToSeconds(segmentEnd)
            startSeconds += float(arguments.pad)
            endSeconds -= float(arguments.pad)

            return self.convertFromSeconds(startSeconds), self.convertFromSeconds(endSeconds)

        # This is so that both pad-beginning and pad-end can go together
        startSeconds = self.convertToSeconds(segmentStart)
        endSeconds = self.convertToSeconds(segmentEnd)

        if arguments.pad_beginning:
            startSeconds += float(arguments.pad_beginning)

        if arguments.pad_end:
            endSeconds -= float(arguments.pad_end)

        return self.convertFromSeconds(startSeconds), self.convertFromSeconds(endSeconds)

    # Could not find any built-in method to do what I want, so here we go
    def convertToSeconds(self, timeString):
        seconds = 0

        separated = timeString.split(":")
        # Strings can have a large decimal point, so float conversion is necessary
        seconds += float(separated[-1])
        seconds += int(separated[-2]) * 60
        if len(separated) > 2:
            seconds += int(separated[-3]) * 3600

        return seconds

    def convertFromSeconds(self, seconds):
        delta = timedelta(seconds=seconds)
        return str(delta)

def parseArgs():
    parser = argparse.ArgumentParser(
        description="YtSplit - Splits a file based on Youtube timestamps.",
        epilog="Note that FFMPEG is required to use this program."
    )

    help_texts = {
        "file": "Destination of file with timestamps",
        "url": "Download timestamps from a Youtube video description (required with --download)",
        "video": "Destination of video file",
        "numerical": "Name videos numerically (useful if file does not follow `timestamp - name` format)",
        "pad": "Pad beginning and end of audio by certain amount of seconds. May help smooth transitions when splitting music compilations.",
        "pad_beginning": "Same as -p, but only for the beginning.",
        "pad_end": "Same as -p, but only for the end.",
        "zero": "Start with the first timestamp at 00:00. Useful if the first timestamp is not there.",
        "download": "Downloads video from youtube (requires youtube-dl)",
        "format": "Specify output format for downloaded video (only for download)",
        "extract_audio": "Tell youtube-dl to extract audio from video",
        "keep": "Keep original video",
        "regex_name": "Specify custom regex for file name",
        "regex_timestamp": "Specify custom regex for timestamp",
        "debug": "Adds extra print statements to show flow of program. Run this to see what the program is doing at a given time."
    }

    videoDestination = parser.add_mutually_exclusive_group(required=True)

    parser.add_argument("-f", "--file",
                        action="store",
                        dest="file",
                        help=help_texts["file"])

    parser.add_argument("-u", "--url",
                        action="store",
                        dest="url",
                        help=help_texts["url"])

    videoDestination.add_argument("-v", "--video",
                        action="store",
                        dest="video",
                        help=help_texts["video"])

    parser.add_argument("-p", "--pad",
                        action="store",
                        dest="pad",
                        help=help_texts["pad"])

    parser.add_argument("-pb", "--pad-beginning",
                        action="store",
                        dest="pad_beginning",
                        help=help_texts["pad_end"])

    parser.add_argument("-pe", "--pad-end",
                        action="store",
                        dest="pad_end",
                        help=help_texts["pad_beginning"])

    parser.add_argument("-n", "--numerical",
                        action="store_true",
                        dest="numerical",
                        help=help_texts["numerical"])

    parser.add_argument("-0", "--zero",
                        action="store_true",
                        dest="zero",
                        help=help_texts["zero"])

    videoDestination.add_argument("--download",
                        action="store_true",
                        dest="download",
                        help=help_texts["download"])

    parser.add_argument("--format",
                        action="store",
                        dest="format",
                        help=help_texts["format"])

    parser.add_argument("--extract-audio",
                        action="store",
                        dest="extract_audio",
                        help=help_texts["extract_audio"])

    parser.add_argument("-k", "--keep",
                        action="store_true",
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

    parser.add_argument("--debug",
                        action="store_true",
                        dest="debug",
                        help=help_texts["debug"])

    return parser.parse_args()

if __name__ == "__main__":
    arguments = parseArgs()
    main()
