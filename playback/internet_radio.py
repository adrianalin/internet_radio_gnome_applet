from collections import namedtuple
import threading
import subprocess
import requests
import re

from . playback import Output
from . sample import Sample


class IceCastClient:
    """
    A simple client for IceCast audio streams.
    The stream method yields blocks of encoded audio data from the stream.
    If the stream has Icy Meta Data, the stream_title attribute will be updated
    with the actual title taken from the meta data.
    """
    def __init__(self, url, block_size=16384):
        self.url = url
        self.stream_format = "???"
        self.stream_title = "???"
        self.station_genre = "???"
        self.station_name = "???"
        self.block_size = block_size
        self._stop_stream = False

    def stop_streaming(self):
        self._stop_stream = True

    def stream(self):
        with requests.get(self. url, stream=True, headers={"icy-metadata": "1"}) as result:
            self.station_genre = result.headers["icy-genre"]
            self.station_name = result.headers["icy-name"]
            self.stream_format = result.headers["Content-Type"]
            if "icy-metaint" in result.headers:
                meta_interval = int(result.headers["icy-metaint"])
            else:
                meta_interval = 0
            if meta_interval:
                audiodata = b""
                for chunk in result.iter_content(self.block_size):
                    if self._stop_stream:
                        return
                    audiodata += chunk
                    if len(audiodata) < meta_interval + 1:
                        continue
                    meta_size = 16 * audiodata[meta_interval]
                    if len(audiodata) < meta_interval + 1 + meta_size:
                        continue
                    metadata = str(audiodata[meta_interval + 1: meta_interval + 1 + meta_size].strip(b"\0"), "utf-8")
                    if metadata:
                        self.stream_title = re.search("StreamTitle='(.*?)'", metadata).group(1)
                    yield audiodata[:meta_interval]
                    audiodata = audiodata[meta_interval + 1 + meta_size:]
                    if self._stop_stream:
                        return
            else:
                for chunk in result.iter_content(self.block_size):
                    if self._stop_stream:
                        break
                    yield chunk


class AudioDecoder:
    """
    Reads streaming audio from an IceCast stream,
    decodes it using ffmpeg, and plays it on the output sound device.

    We need two threads:
     1) main thread that spawns ffmpeg, reads radio stream data, and writes that to ffmpeg
     2) background thread that reads decoded audio data from ffmpeg and plays it
    """
    def __init__(self, icecast_client, song_title_callback=None):
        self.client = icecast_client
        self.stream_title = "???"
        self.song_title_callback = song_title_callback
        self.ffmpeg_process = None

    def stop_playback(self):
        if self.ffmpeg_process:
            self.ffmpeg_process.stdin.close()
            self.ffmpeg_process.stdout.close()
            self.ffmpeg_process.kill()
            self.ffmpeg_process = None

    def _audio_playback(self, ffmpeg_stream):
        # thread 3: audio playback

        def played(sample):
            if self.client.stream_title != self.stream_title:
                self.stream_title = self.client.stream_title
                if self.song_title_callback:
                    self.song_title_callback(self.stream_title)
                else:
                    print("\n\nNew Song:", self.stream_title, "\n")

        with Output(mixing="sequential", frames_per_chunk=44100//4) as output:
            output.register_notify_played(played)
            while True:
                try:
                    audio = ffmpeg_stream.read(44100 * 2 * 2 // 10)
                    if not audio:
                        break
                except (IOError, ValueError):
                    break
                else:
                    sample = Sample.from_raw_frames(audio, 2, 44100, 2)
                    output.play_sample(sample)

    def stream_radio(self):
        stream = self.client.stream()
        first_chunk = next(stream)
        format = ""
        if self.client.stream_format == "audio/mpeg":
            format = "mp3"
        elif self.client.stream_format.startswith("audio/aac"):
            format = "aac"
        if not self.song_title_callback:
            print("\nStreaming Radio Station: ", self.client.station_name)
        cmd = ["ffmpeg", "-v", "fatal", "-nostdin", "-i", "-"]
        if format:
            cmd.extend(["-f", format])
        # cmd.extend(["-af", "aresample=resampler=soxr"])     # enable this if your ffmpeg has sox hq resample
        cmd.extend(["-ar", "44100", "-ac", "2", "-acodec", "pcm_s16le", "-f", "s16le", "-"])
        self.ffmpeg_process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        self.ffmpeg_process.stdin.write(first_chunk)
        audio_playback_thread = threading.Thread(target=self._audio_playback, args=[self.ffmpeg_process.stdout], daemon=True)
        audio_playback_thread.start()

        try:
            for chunk in stream:
                if self.ffmpeg_process:
                    self.ffmpeg_process.stdin.write(chunk)
                else:
                    break
        except BrokenPipeError:
            pass
        except KeyboardInterrupt:
            pass
        finally:
            self.stop_playback()
            audio_playback_thread.join()
            if not self.song_title_callback:
                print("\n")


class Internetradio:
    StationDef = namedtuple("StationDef", ["station_name", "stream_url"])
    stations = [
        StationDef("Soma FM", "http://ice3.somafm.com/groovesalad-64-aac"),
        StationDef("Soma FM", "http://ice3.somafm.com/secretagent-64-aac"),
        StationDef("University of Calgary", "http://stream.cjsw.com:80/cjsw.ogg"),
        StationDef("Playtrance.com", "http://live.playtrance.com:8000/playtrance-livetech.aac")
    ]

    def __init__(self):
        self.song_title = "..."
        self.play_thread = None
        self.stream_name_label = None
        self.icyclient = None
        self.decoder = None

    def play_station(self, st):
        station = None
        if isinstance(st, self.StationDef):
            station = st
        elif isinstance(st, int):
            station = self.stations[st]

        if self.is_playing():
            self.stop()
        self.stream_name_label = "{}".format(station.station_name)
        self.icyclient = IceCastClient(station.stream_url, 8192)
        self.decoder = AudioDecoder(self.icyclient, self.set_song_title)
        self.set_song_title("...")
        self.play_thread = threading.Thread(target=self.decoder.stream_radio, daemon=True)
        self.play_thread.start()

    def set_song_title(self, title):
        self.song_title = title

    def is_playing(self):
        return self.play_thread is not None

    def stop(self):
        self.song_title = "(stoping...)"
        self.icyclient.stop_streaming()
        # this doesn't work properly on Windows, it hangs. Therefore we close the http stream.
        # self.decoder.stop_playback()
        self.decoder = None
        self.play_thread.join()
        self.play_thread = None


internetRadio = Internetradio()
