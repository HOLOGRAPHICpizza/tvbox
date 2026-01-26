# final program in the tvbox launch chain
# ran by tvboxlaunchchain2
# don't even think about importing this file

import os
import sys
import asyncio
import json
import vlc
import time
import signal
import threading

def pwint(_object):
    print(_object, flush=True)

def pwint_err(_object):
    print(_object, file=sys.stderr, flush=True)

# load environment variables
try:
    TVBOX_FULLSCREEN = os.environ['TVBOX_FULLSCREEN'] == '1'
    TVBOX_GPIO = os.environ['TVBOX_GPIO'] == '1'
    TVBOX_LIRC = os.environ['TVBOX_LIRC'] == '1'
    TVBOX_DEBUG = os.environ['TVBOX_DEBUG'] == '1'
    TVBOX_VAAPI = os.environ['TVBOX_VAAPI'] == '1'

    TVBOX_DIR = os.environ['TVBOX_DIR']
    TVBOX_CHANNELS_DIR = os.environ['TVBOX_CHANNELS_DIR']
    TVBOX_PAUSE_DELAY = float(os.environ['TVBOX_PAUSE_DELAY'])
except (KeyError, ValueError) as _e:
    pwint_err('Environment variables could not be read.')
    pwint_err(_e)
    sys.exit(1)

if TVBOX_GPIO:
    import gpiozero

    SEGMENT_PINS = (
        gpiozero.LED('GPIO26'), # A
        gpiozero.LED('GPIO19'), # B
        gpiozero.LED('GPIO13'), # C
        gpiozero.LED('GPIO6'),  # D
        gpiozero.LED('GPIO5'),  # E
        gpiozero.LED('GPIO11'), # F
        gpiozero.LED('GPIO9')   # G
    )

    DIGIT_PINS = (
        gpiozero.LED('GPIO20'), # DIGIT 1
        gpiozero.LED('GPIO21')  # DIGIT 2
    )

    DIGIT_SEGMENTS = {
        ' ': (False, False, False, False, False, False, False),
        '0': (True, True, True, True, True, True, False),
        '1': (False, True, True, False, False, False, False),
        '2': (True, True, False, True, True, False, True),
        '3': (True, True, True, True, False, False, True),
        '4': (False, True, True, False, False, True, True),
        '5': (True, False, True, True, False, True, True),
        '6': (True, False, True, True, True, True, True),
        '7': (True, True, True, False, False, False, False),
        '8': (True, True, True, True, True, True, True),
        '9': (True, True, True, True, False, True, True)
    }

    def set_segments(numeral: str):
        for segment in range(7):
            if DIGIT_SEGMENTS[numeral][segment]:
                SEGMENT_PINS[segment].on()
            else:
                SEGMENT_PINS[segment].off()

if TVBOX_LIRC:
    import lirc

# load state
if 'XDG_STATE_HOME' in os.environ:
    STATE_FILE = os.path.join(os.environ['XDG_STATE_HOME'], 'tvboxstaterc')
else:
    _state_dir = os.path.expanduser("~/.local/state/")
    os.makedirs(_state_dir, exist_ok=True)
    STATE_FILE = os.path.join(_state_dir, 'tvboxstaterc')

state = {
    'last_channel': 1,   # default to channel 1
    'channel_clocks': {}
}
try:
    with open(STATE_FILE, 'r') as _file:
        state = json.load(_file)
except (OSError, json.JSONDecodeError, UnicodeDecodeError):
    pwint('Could not read ' + STATE_FILE)

# clock that continues to "run" while the program is not running, relies on accurate system time
class Clock(object):
    offset: int     # the saved up sum of clock times from each time the clock was stopped
    running: bool   # is the clock currently running
    start_time: int # unix time of when the clock was started

    def __init__(self, offset: int = 0, running: bool = False, start_time: int = 0):
        self.offset = offset
        self.running = running
        self.start_time = start_time

    def clocktime(self) -> int:
        if self.running:
            return self.offset + (int(time.time()) - self.start_time)
        else:
            return self.offset

    def start(self):
        assert self.running == False
        self.start_time = int(time.time())
        self.running = True

    def stop(self):
        assert self.running == True
        self.offset = self.clocktime()
        self.running = False

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
    clock: Clock

    def add_episode(self, filename: str, length: int):
        if len(self.episodes) == 0:
            start_time = 0
        else:
            start_time = self.episodes[-1].start_time + self.episodes[-1].length
        self.episodes.append(Episode(filename, start_time, length))
        self.length += length

    def __init__(self, channel_file: str, clocktime: int, running: bool, start_time: int):
        self.length = 0
        self.episodes = []
        self.current_episode_num = 0
        self.clock = Clock(clocktime, running, start_time)

        # we want shit indexed starting at 1
        self.add_episode('INVALID PLACEHOLDER EPISODE', 0)
        if channel_file == 'INVALID PLACEHOLDER CHANNEL':
            return

        pwint('reading ' + channel_file)

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

        pwint("\nplaying channel " + str(self.current_channel_num)
              + ' episode ' + str(self.current_channel().current_episode_num)
              + ' ' + filename)

        self.vlc_player.stop()
        if self.vlc_media_instance is not None:
            self.vlc_media_instance.release()

        self.vlc_media_instance = self.vlc_instance.media_new(filename)
        if TVBOX_VAAPI: # need this to work on skylake
            self.vlc_media_instance.add_option(':avcodec-hw=vaapi')
        self.vlc_player.set_media(self.vlc_media_instance)

        self.vlc_player.play()

        # pause after a delay to make sure it takes effect, then again after 1 sec for good measure
        self.event_loop.call_later(TVBOX_PAUSE_DELAY, self.event_loop.call_soon_threadsafe, pause_vlc_maybe)
        self.event_loop.call_later(TVBOX_PAUSE_DELAY + 1.0, self.event_loop.call_soon_threadsafe, pause_vlc_maybe)

        if TVBOX_FULLSCREEN:
            _delay = 0.2
            while _delay <= 2.0:
                self.event_loop.call_later(_delay, self.event_loop.call_soon_threadsafe, self.vlc_player.set_fullscreen, True)
                _delay = _delay + 0.2

    def play_channel(self, channel_num: int):
        assert threading.current_thread() == threading.main_thread()

        # set current channel number
        self.current_channel_num = channel_num

        # save state
        save_state()

        #print('play channel ' + str(channel_num))

        # find time in playlist as a whole
        time_in_playlist: int = int(self.current_channel().clock.clocktime() % self.current_channel().length)
        #print('playlist length ' + str(self.current_channel().length))
        #print('time in playlist ' + str(time_in_playlist), flush=True)

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
        time_in_episode: int = time_in_playlist - self.current_channel().episodes[episode_num].start_time
        pwint('seeking to ' + str(time_in_episode) + 'sec - pos in episode '
              + format(time_in_episode / self.current_channel().episodes[episode_num].length, ".0%")
              + ' - pos in channel ' + format(time_in_playlist / self.current_channel().length, ".0%"))
        self.vlc_player.set_time(time_in_episode * 1000)
        #print('episode length ' + str(self.current_channel().episodes[episode_num].length))
        #print('time in episode ' + str(time_in_episode))

    def __init__(self, event_loop: asyncio.AbstractEventLoop):
        self.event_loop = event_loop
        # we want the first channel to be index 1
        self.channels = [Channel('INVALID PLACEHOLDER CHANNEL', 0, False, 0)]
        self.current_channel_num = 1

        self.vlc_instance = vlc.Instance('--no-spu') # subtitles disabled
        self.vlc_player = self.vlc_instance.media_player_new()
        self.vlc_media_instance = None

def custom_exception_handler(loop, context):
    # first, handle with default handler
    loop.default_exception_handler(context)

    #exception = context.get('exception')
    pwint_err(context)
    loop.stop()
    sys.exit(1)

class TermException(Exception):
    pass

def sigterm_handler(_signo, _stack_frame):
    raise TermException

if __name__ == '__main__':
    if len(sys.argv) < 2:
        pwint_err('Usage: ' + sys.argv[0] + ' channel_file_dir')
        sys.exit(1)
    channel_file_dir = os.path.abspath(sys.argv[1])

    #print('Main thread: ' + str(threading.get_ident()))
    pwint('tvbox started')

    signal.signal(signal.SIGTERM, sigterm_handler)

    _event_loop = asyncio.get_event_loop()
    _event_loop.set_debug(False)
    _event_loop.set_exception_handler(custom_exception_handler)

    tv = TV(_event_loop)

    # save state to variable and to file
    # the only time the state should need saving is after pausing or unpausing, and after changing channels
    def save_state():
        state['last_channel'] = tv.current_channel_num

        for i in range(1, len(tv.channels)):
            state['channel_clocks'][str(i)] = (tv.channels[i].clock.offset,
                                               tv.channels[i].clock.running,
                                               tv.channels[i].clock.start_time)

        # write the state to disk
        try:
            with open(STATE_FILE, 'w') as file:
                json.dump(state, file, indent=2)
        except OSError:
            pwint('Could not write ' + STATE_FILE)

    def next_channel():
        pwint('next channel')
        channel_num = tv.current_channel_num + 1
        # tv.channels has a dummy channel, i.e. indexed from 1
        if channel_num == len(tv.channels):
            # loop around
            channel_num = 1
        tv.event_loop.call_soon_threadsafe(tv.play_channel, channel_num)

    def prev_channel():
        pwint('previous channel')
        channel_num = tv.current_channel_num - 1
        # tv.channels has a dummy channel, i.e. indexed from 1
        if channel_num == 0:
            # loop around
            channel_num = len(tv.channels) - 1
        tv.event_loop.call_soon_threadsafe(tv.play_channel, channel_num)

    def next_episode():
        pwint('next episode')

    def sigusr1_handler(_signo, _stack_frame):
        next_channel()

    def sigusr2_handler(_signo, _stack_frame):
        prev_channel()

    def pause_toggle():
        assert threading.current_thread() == threading.main_thread()

        if tv.current_channel().clock.running:
            pwint('pause toggle: clock is running, time to pause')
            # pause
            tv.current_channel().clock.stop()
            if not 'Paused' in str(tv.vlc_player.get_state()):
                pwint('pause toggle: vlc pause toggle')
                tv.vlc_player.pause()

        else:
            pwint('pause toggle: clock is not running, time to unpause')
            # unpause
            tv.current_channel().clock.start()
            if 'Paused' in str(tv.vlc_player.get_state()):
                pwint('pause toggle: vlc pause toggle')
                tv.vlc_player.pause()

        save_state()

    # pause vlc if the channel is supposed to be paused and vlc is not paused
    def pause_vlc_maybe():
        assert threading.current_thread() == threading.main_thread()

        # if supposed to be paused and is not paused
        if (not tv.current_channel().clock.running) and not 'Paused' in str(tv.vlc_player.get_state()):
            pwint('pause maybe? yes')
            tv.vlc_player.pause()

    # next episode
    # noinspection PyUnusedLocal
    def media_end_handler(event: vlc.Event):
        #print('media_end_handler thread: ' + str(threading.get_ident()))

        # python-vlc is not reentrant, we must control vlc from the main thread
        tv.event_loop.call_soon_threadsafe(tv.play_channel, tv.current_channel_num)

    if TVBOX_LIRC:
        def ir_loop():
            # get IR command
            # keypress format = (hexcode, repeat_num, command_key, remote_id)
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
                        elif command == 'KEY_PAUSE':
                            # noinspection PyTypeChecker
                            tv.event_loop.call_soon_threadsafe(pause_toggle)

    if TVBOX_GPIO:
        def seven_seg_loop():
            first_digit = True
            while True:
                num_str = str(tv.current_channel_num).rjust(2, ' ')

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
        for dirpath, dirnames, files in os.walk(channel_file_dir):
            files.sort()
            for name in files:
                if name.endswith('.channel'):
                    # read channel clock from state
                    _offset = 0
                    _running = True
                    _start_time = int(time.time())
                    if str(len(tv.channels)) in state['channel_clocks']:
                        _offset, _running, _start_time = state['channel_clocks'][str(len(tv.channels))]

                    tv.add_channel(Channel(os.path.join(dirpath, name), _offset, _running, _start_time))
        if len(tv.channels) < 2:
            pwint_err('No .channel files found.')
            sys.exit(1)

        # start playback
        tv.play_channel(state['last_channel'])

        # media end handler
        event_manager = tv.vlc_player.event_manager()
        event_manager.event_attach(vlc.EventType.MediaPlayerEndReached, media_end_handler)

        if TVBOX_GPIO:
            # buttons
            next_button = gpiozero.Button('GPIO17', pull_up=True, bounce_time=0.05)
            next_button.when_pressed = next_channel

            prev_button = gpiozero.Button('GPIO27', pull_up=True, bounce_time=0.05)
            prev_button.when_pressed = prev_channel

            # 7-segment display
            # noinspection PyUnboundLocalVariable
            seven_seg_thread = threading.Thread(group=None, target=seven_seg_loop, name='seven_seg_thread')
            seven_seg_thread.daemon = True
            seven_seg_thread.start()

        # IR remote
        if TVBOX_LIRC:
            # noinspection PyUnboundLocalVariable
            ir_thread = threading.Thread(group=None, target=ir_loop, name='ir_thread')
            ir_thread.daemon = True   # Kills the thread when the program exits
            ir_thread.start()

        tv.event_loop.run_forever()

    except KeyboardInterrupt:
        pwint('Caught SIGINT, tvbox exiting.')

    except TermException:
        pwint('Caught SIGTERM, tvbox exiting.')

    finally:
        # Stop playback and release resources
        tv.vlc_player.stop()
        if tv.vlc_media_instance is not None:
            tv.vlc_media_instance.release()
        tv.vlc_player.release()
        tv.event_loop.close()
