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
        #TODO Allow user to use video name as big file name
        ydlOpts = {'outtmpl': 'ytdl-output.%(ext)s'}
        # Most videos are merged into mkv by default.
        #TODO: fails if it merges to webm instead
        self.outputFormat = "mkv"

        if arguments.format:
            self.outputFormat = arguments.format
            ydlOpts["recodevideo"] = self.outputFormat
        elif arguments.extract_audio:
            self.outputFormat = arguments.extract_audio
            ydlOpts["extractaudio"] = True
            ydlOpts["audioformat"] = arguments.extract_audio

        return ydlOpts

class VideoManipulator:
    def __init__(self, timestamps):
        downloader = VideoDownloader()
        self.timestampManip = TimestampManipulator()

        self.timestamps = timestamps
        self.videoName = downloader.getVideo()
        self.timestampManip.loadVideoSilences(self.videoName)
        self.fileFormat = self.getFileFormat(self.videoName)

    def splitVideo(self):
        currentTime = self.timestampManip.getStartingTime(self.timestamps[0][0])
        videoDuration = self.getVideoDuration(self.videoName)
        segmentNumber = 1

        for stamp in self.timestamps:
            name = self.getSegmentName(str(segmentNumber), stamp[1])

            endTime = self.timestampManip.getEndTime(videoDuration, segmentNumber, self.timestamps)

            processedStart, processedEnd = self.timestampManip.padTimestamps(currentTime, endTime)
            processedStart, processedEnd = self.timestampManip.silenceSplit(processedStart, processedEnd)

            #TODO make this work
            # command = ["ffmpeg", "-ss", currentTime, "-t", endTime, "-i", videoName, "-acodec", "copy", "-vcodec", "copy", "\"" + name + "." + fileFormat + "\""]
            # subprocess.call(command)

            command = f"ffmpeg -hide_banner -loglevel error -ss {processedStart} -to {processedEnd} -i {self.videoName} -acodec copy -vcodec copy \"{name}.{self.fileFormat}\""
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
            remove(self.videoName)

    def getFileFormat(self, videoName):
        fileFormat = re.search("(?<=\.)\w*", videoName)
        if not fileFormat:
            print("Could not find file extension in file name. Quitting.")
            quit()

        return fileFormat.group(0)

    def getVideoDuration(self, videoName):
        command = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", "-sexagesimal", videoName]
        duration = subprocess.check_output(command).decode("utf-8")

        return re.sub("'|\n", "", duration)

class TimestampManipulator:
    def loadVideoSilences(self, fileName):
        if arguments.intelligent:
            silence = SilenceFinder()
            self.silenceTimestamps = silence.getSilenceTimestamps(fileName)

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

    def silenceSplit(self, segmentStart, segmentEnd):
        if arguments.intelligent:
            startSeconds = self.convertToSeconds(segmentStart)
            endSeconds = self.convertToSeconds(segmentEnd)

            # Loops through every silence timestamp ffmpeg detected and checks
            # whether it is more than arguments.intelligent_time seconds away
            # from a given timestamp
            for stamp in self.silenceTimestamps:
                difference = abs(startSeconds - stamp[1])
                if difference < arguments.intelligent_time:
                    segmentStart = self.convertFromSeconds(stamp[1])
                    break

            for stamp in self.silenceTimestamps:
                difference = abs(endSeconds - stamp[0])
                if difference < arguments.intelligent_time:
                    segmentEnd = self.convertFromSeconds(stamp[0])
                    break

        return segmentStart, segmentEnd

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

class SilenceFinder:
    def getSilenceTimestamps(self, fileName):
        print("Retrieving silent parts of video for --intelligent. This may take several minutes.")
        cmd = f"ffmpeg -i {fileName} -af silencedetect=d=0.5:n=0.03 -f null -"
        args = cmd.split()
        # FFMPEG only properly output to subprocess.Popen due to the way it buffers lines
        process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,universal_newlines=True)
        # Process runs parallel to ytsplit, so wait for it to finish first
        process.wait()

        silence = self.readSilenceTimestamps(process.stdout.read().splitlines())

        return silence

    def readSilenceTimestamps(self, output):
        silence = []
        pair = [None, None]

        for line in output:
            start = self.checkStartRegex(line)
            end = self.checkEndRegex(line)

            if start:
                pair[0] = float(start)
            elif end:
                pair[1] = float(end)

            if pair[0] and pair[1]:
                silence.append(pair)
                pair = [None, None]

        return silence

    def checkStartRegex(self, line):
        startRegex = "(?<=silence_start:\ )\d*\.?\d*"
        silenceStart = 0

        match = re.search(startRegex, line)

        if match:
            time = match.group(0)
            return time
        else:
            return None

    def checkEndRegex(self, line):
        endRegex = "(?<=silence_end:\ )\d*\.?\d*"
        silenceStart = 0

        match = re.search(endRegex, line)

        if match:
            time = match.group(0)
            return time
        else:
            return None

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
        "intelligent": "Attempts to intelligently detect transitions between tracks based on whether there is silence next to the timestamp. Not guaranteed to work.",
        "intelligent_duration": "Minimum duration of silence for it to be noticed. Usable only with --intelligent. Default: 0.5",
        "intelligent_sensitivity": "Sensitivity of silence detector. Higher means more sensitive. Do not set the value too high. Usable only with --intelligent. Default: 0.03",
        "intelligent_time": "How many seconds ahead and behind the timestamp silence detector will search. Usable only with --intelligent. Default: 3",
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

    parser.add_argument("-i", "--intelligent",
                        action="store_true",
                        dest="intelligent",
                        help=help_texts["intelligent"])

    parser.add_argument("-id", "--intelligent-duration",
                        action="store_true",
                        dest="intelligent_duration",
                        default=0.5,
                        help=help_texts["intelligent_duration"])

    parser.add_argument("-is", "--intelligent-sensitivity",
                        action="store_true",
                        dest="intelligent_sensitivity",
                        default=0.3,
                        help=help_texts["intelligent_sensitivity"])

    parser.add_argument("-it", "--intelligent-time",
                        action="store_true",
                        dest="intelligent_time",
                        default=3,
                        help=help_texts["intelligent_time"])

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
