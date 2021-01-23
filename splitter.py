#!/usr/bin/python3

import re
import argparse
import subprocess
import youtube_dl
from os import remove

version = "1.0.0 - Release"

def main():
    timestamps = TimestampRetriever()
    splitter = VideoManipulator(timestamps.getTimestamps())
    splitter.splitVideo()

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
            ydlOpts = self.setDownloadOptions()
            self.downloadVideo(ydlOpts)

            return "ytdl-output." + self.outputFormat

    def downloadVideo(self, ydlOpts):
        with youtube_dl.YoutubeDL(ydlOpts) as ydl:
            ydl.download([arguments.url])

    # Downloads video if asked for it. If not, just returns video file name.
    def setDownloadOptions(self):
        ydlOpts = {'outtmpl': 'ytdl-output.%(ext)s'}
        # Most videos are merged into mkv by default.
        self.outputFormat = "mkv"

        if arguments.format:
            self.outputFormat = arguments.format
            ydlOpts["recodevideo"] = arguments.format
        elif arguments.extract_audio:
            self.outputFormat = arguments.extract_audio
            ydlOpts["extractaudio"] = True
            ydlOpts["audioformat"] = arguments.extract_audio

        return ydlOpts

class VideoManipulator:
    def __init__(self, timestamps):
        downloader = VideoDownloader()

        self.timestamps = timestamps
        self.videoName = downloader.getVideo()
        self.fileFormat = self.getFileFormat(self.videoName)

    def splitVideo(self):
        currentTime = self.getStartingTime(self.timestamps[0][0])
        videoDuration = self.getVideoDuration(self.videoName)
        segmentNumber = 1

        for stamp in self.timestamps:
            name = self.getSegmentName(str(segmentNumber), stamp[1])

            endTime = self.getEndTime(videoDuration, segmentNumber)

            #TODO make this work
            # command = ["ffmpeg", "-ss", currentTime, "-t", endTime, "-i", videoName, "-acodec", "copy", "-vcodec", "copy", "\"" + name + "." + fileFormat + "\""]
            # subprocess.call(command)

            command = f"ffmpeg -ss {currentTime} -to {endTime} -i {self.videoName} -acodec copy -vcodec copy \"{name}.{self.fileFormat}\""
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

    def getStartingTime(self, firstTimestamp):
        if arguments.zero:
            return "0:00"
        else:
            return firstTimestamp

    # Deletes the split video unless -k was passed
    def removeOriginal(self):
        if not arguments.keep:
            remove(self.videoName)

    def getFileFormat(self, videoName):
        print(videoName)
        fileFormat = re.search("(?<=\.)\w*", videoName)
        if not fileFormat:
            print("Could not find file extension in file name. Quitting.")
            quit()

        return fileFormat.group(0)

    def getVideoDuration(self, videoName):
        command = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", "-sexagesimal", videoName]
        duration = subprocess.check_output(command).decode("utf-8")

        return re.sub("'|\n", "", duration)

    def getEndTime(self, videoDuration, segmentNumber):
        if segmentNumber == len(self.timestamps):
            return videoDuration
        else:
            return self.timestamps[segmentNumber][0]

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
        "zero": "Start with the first timestamp at 00:00. Useful if the first timestamp is not there.",
        "download": "Downloads video from youtube (requires youtube-dl)",
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
                        help=help_texts["file"])

    parser.add_argument("-u", "--url",
                        action="store",
                        dest="url",
                        help=help_texts["url"])

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

    return parser.parse_args()

if __name__ == "__main__":
    arguments = parseArgs()
    main()
