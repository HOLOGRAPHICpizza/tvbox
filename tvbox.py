import asyncio
import vlc
import time
import signal
import threading
import sys
import os
import gpiozero
import lirc

LAST_CHANNEL_FILE = os.path.expanduser("~/.tvbox")

SEGMENT_PINS = (
    gpiozero.LED('GPIO26'),       # A
    gpiozero.LED('GPIO19'),       # B
    gpiozero.LED('GPIO13'),       # C
    gpiozero.LED('GPIO6'),        # D
    gpiozero.LED('GPIO5'),        # E
    gpiozero.LED('GPIO11'),       # F
    gpiozero.LED('GPIO9')         # G
)

DIGIT_PINS = (
    gpiozero.LED('GPIO20', active_high=False), # DIGIT 1
    gpiozero.LED('GPIO21', active_high=False)  # DIGIT 2
)

DIGIT_SEGMENTS = {
    ' ':(False,False,False,False,False,False,False),
    '0':(True,True,True,True,True,True,False),
    '1':(False,True,True,False,False,False,False),
    '2':(True,True,False,True,True,False,True),
    '3':(True,True,True,True,False,False,True),
    '4':(False,True,True,False,False,True,True),
    '5':(True,False,True,True,False,True,True),
    '6':(True,False,True,True,True,True,True),
    '7':(True,True,True,False,False,False,False),
    '8':(True,True,True,True,True,True,True),
    '9':(True,True,True,True,False,True,True)
}

# do not create directly, use Channel.addEpisode
class Episode(object):
    filename: str
    start_time: int
    length: int

    def __init__(self, filename: str, start_time: int, length: int):
        self.filename = filename
        self.start_time = start_time
        self.length = length

class Channel(object):
    length: int
    episodes: list[Episode]
    current_episode_num: int

    def add_episode(self, filename: str, length: int):
        if len(self.episodes) == 0:
            start_time = 0
        else:
            start_time = self.episodes[-1].start_time + self.episodes[-1].length
        self.episodes.append(Episode(filename, start_time, length))
        self.length += length

    def __init__(self, channel_file: str):
        self.length = 0
        self.episodes = []
        self.current_episode_num = 0

        # we want shit indexed starting at 1
        self.add_episode('INVALID PLACEHOLDER EPISODE', 0)
        if channel_file == 'INVALID PLACEHOLDER CHANNEL':
            return

        print('reading ' + channel_file, flush=True)

        # change working directory to location of channel file
        channel_file = os.path.abspath(channel_file)
        os.chdir(os.path.dirname(channel_file))

        with open(channel_file, 'r') as file:
                for line in file:
                    fields = line.split('|')
                    abs_path = os.path.abspath(fields[0])
                    self.add_episode(abs_path, int(fields[1]))

class TV(object):
    event_loop: asyncio.AbstractEventLoop
    channels: list[Channel]
    current_channel_num: int
    vlc_instance: vlc.Instance
    vlc_player: vlc.MediaPlayer

    def current_channel(self):
        return self.channels[self.current_channel_num]

    def add_channel(self, channel: Channel):
        self.channels.append(channel)

    def play_file(self, filename: str):
        assert threading.current_thread() == threading.main_thread()

        print("\nplaying channel " + str(self.current_channel_num)
              + ' episode ' + str(self.current_channel().current_episode_num)
              + ' ' + filename, flush=True)

        self.vlc_player.set_fullscreen(False)
        self.vlc_player.stop()
        if self.vlc_media_instance is not None:
            self.vlc_media_instance.release()

        #TODO: error handling
        self.vlc_media_instance = self.vlc_instance.media_new(filename)
        self.vlc_player.set_media(self.vlc_media_instance)
        self.vlc_player.play()

        #TODO: make this a cmd line arg
        self.vlc_player.set_fullscreen(True)

    def play_channel(self, channel_num: int):
        assert threading.current_thread() == threading.main_thread()

        self.current_channel_num = channel_num
        write_last_channel(channel_num)
        #print('play channel ' + str(channel_num))

        # find time in playlist as a whole
        time_in_playlist = int(time.time()) % self.current_channel().length
        #print('playlist length ' + str(self.current_channel().length))
        #print('time in playlist ' + str(time_in_playlist))

        # determine episode
        episode_num = 1
        for i in range(len(self.current_channel().episodes)):
            e = self.current_channel().episodes[i]
            if e.start_time <= time_in_playlist < (e.start_time + e.length):
                episode_num = i
                break
        self.current_channel().current_episode_num = episode_num
        #print('episode num ' + str(episode_num))
        #print('filename ' + self.current_channel().episodes[episode_num].filename)

        self.play_file(self.current_channel().episodes[episode_num].filename)

        # find time in episode
        time_in_episode = time_in_playlist - self.current_channel().episodes[episode_num].start_time
        print('seeking to ' + str(time_in_episode) + 'sec - pos in episode '
              + format(time_in_episode / self.current_channel().episodes[episode_num].length, ".0%")
              + ' - pos in channel ' + format(time_in_playlist / self.current_channel().length, ".0%"), flush=True)
        self.vlc_player.set_time(time_in_episode * 1000)
        #print('episode length ' + str(self.current_channel().episodes[episode_num].length))
        #print('time in episode ' + str(time_in_episode))

    def __init__(self, event_loop: asyncio.AbstractEventLoop):
        self.event_loop = event_loop
        # we want the first channel to be index 1
        self.channels = [Channel('INVALID PLACEHOLDER CHANNEL')]
        self.current_channel_num = 1

        self.vlc_instance = vlc.Instance('--no-spu') # subtitles disabled
        self.vlc_player = self.vlc_instance.media_player_new()
        self.vlc_media_instance = None

def custom_exception_handler(loop, context):
    # first, handle with default handler
    loop.default_exception_handler(context)

    #exception = context.get('exception')
    print(context, flush=True)
    loop.stop()
    sys.exit(1)

class TermException(Exception):
    pass

def sigterm_handler(_signo, _stack_frame):
    raise TermException

def read_last_channel():
    try:
        with open(LAST_CHANNEL_FILE, 'r') as file:
            channel = int(file.read())
            return channel
    except (OSError, ValueError):
        print('Could not read ' + LAST_CHANNEL_FILE, flush=True)

    # default to channel 1
    return 1

def write_last_channel(channel: int):
    try:
        with open(LAST_CHANNEL_FILE, 'w') as file:
            file.write(str(channel))
    except OSError:
        print('Could not write ' + LAST_CHANNEL_FILE, flush=True)

def set_segments(numeral: str):
    for segment in range(7):
        if DIGIT_SEGMENTS[numeral][segment]:
            SEGMENT_PINS[segment].on()
        else:
            SEGMENT_PINS[segment].off()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: ' + sys.argv[0] + ' channel_file_dir', file=sys.stderr, flush=True)
        sys.exit(1)
    channel_file_dir = os.path.abspath(sys.argv[1])

    #print('Main thread: ' + str(threading.get_ident()))
    print('tvbox started', flush=True)

    signal.signal(signal.SIGTERM, sigterm_handler)

    _event_loop = asyncio.get_event_loop()
    _event_loop.set_debug(False)
    _event_loop.set_exception_handler(custom_exception_handler)

    tv = TV(_event_loop)

    def next_channel():
        print('next channel', flush=True)
        channel_num = tv.current_channel_num + 1
        # tv.channels has a dummy channel, i.e. indexed from 1
        if channel_num == len(tv.channels):
            # loop around
            channel_num = 1
        tv.event_loop.call_soon_threadsafe(tv.play_channel, channel_num)

    def prev_channel():
        print('previous channel', flush=True)
        channel_num = tv.current_channel_num - 1
        # tv.channels has a dummy channel, i.e. indexed from 1
        if channel_num == 0:
            # loop around
            channel_num = len(tv.channels) - 1
        tv.event_loop.call_soon_threadsafe(tv.play_channel, channel_num)

    def sigusr1_handler(_signo, _stack_frame):
        next_channel()

    def sigusr2_handler(_signo, _stack_frame):
        prev_channel()

    # next episode
    def media_end_handler(event: vlc.Event):
        #print('media_end_handler thread: ' + str(threading.get_ident()))

        # python-vlc is not reentrant, we must control vlc from the main thread
        tv.event_loop.call_soon_threadsafe(tv.play_channel, tv.current_channel_num)

    def ir_loop():
        #get IR command
        #keypress format = (hexcode, repeat_num, command_key, remote_id)
        with lirc.RawConnection() as conn:
            while True:
                keypress = conn.readline() # blocking read
                sequence = keypress.split()[1]
                command = keypress.split()[2]

                #ignore command repeats
                if sequence == "00":
                    if command == 'KEY_CHANNELUP':
                        next_channel()
                    elif command == 'KEY_CHANNELDOWN':
                        prev_channel()

    def seven_seg_loop():
        first_digit = True
        while True:
            num_str = str(tv.current_channel_num).rjust(2, ' ')
            #num_str = str(int(time.time()))[-2:]

            if first_digit:
                DIGIT_PINS[1].off()
                set_segments(num_str[-2])
                DIGIT_PINS[0].on()
            else:
                DIGIT_PINS[0].off()
                set_segments(num_str[-1])
                DIGIT_PINS[1].on()

            first_digit = not first_digit
            time.sleep(0.005)

    signal.signal(signal.SIGUSR1, sigusr1_handler)
    signal.signal(signal.SIGUSR2, sigusr2_handler)

    try:
        #TODO: load channels in order
        for dirpath, dirnames, files in os.walk(channel_file_dir):
            files.sort()
            for name in files:
                if name.endswith('.channel'):
                    tv.add_channel(Channel(os.path.join(dirpath, name)))
        if len(tv.channels) < 2:
            print('No .channel files found.', file=sys.stderr, flush=True)
            sys.exit(1)

        tv.play_channel(read_last_channel())

        event_manager = tv.vlc_player.event_manager()
        event_manager.event_attach(vlc.EventType.MediaPlayerEndReached, media_end_handler)

        # buttons
        next_button = gpiozero.Button('GPIO17', pull_up=False, bounce_time=0.05)
        next_button.when_pressed = next_channel

        prev_button = gpiozero.Button('GPIO27', pull_up=False, bounce_time=0.05)
        prev_button.when_pressed = prev_channel

        # IR remote
        ir_thread = threading.Thread(group=None, target=ir_loop, name='ir_thread')
        ir_thread.daemon = True   # Kills the thread when the program exits
        ir_thread.start()

        # 7-segment display
        seven_seg_thread = threading.Thread(group=None, target=seven_seg_loop, name='seven_seg_thread')
        seven_seg_thread.daemon = True
        seven_seg_thread.start()

        tv.event_loop.run_forever()

    except KeyboardInterrupt:
        print('Caught SIGINT, tvbox exiting.', flush=True)

    except TermException:
        print('Caught SIGTERM, tvbox exiting.', flush=True)

    finally:
        # Stop playback and release resources
        tv.vlc_player.stop()
        if tv.vlc_media_instance is not None:
            tv.vlc_media_instance.release()
        tv.vlc_player.release()
        tv.event_loop.close()
