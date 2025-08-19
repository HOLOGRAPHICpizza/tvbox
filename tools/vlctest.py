# nothing works, I can not catch errors from vlc

import vlc
import time

def media_error_handler(event: vlc.Event):
    # never freaking gets called
    print('ERROR', flush=True)
    print(event)

instance = vlc.Instance()
player = instance.media_player_new()

event_manager = player.event_manager()
event_manager.event_attach(vlc.EventType.MediaPlayerEncounteredError, media_error_handler)

#media = instance.media_new('/home/michael/tvbox_media/Mythbusters/S07/Dropping A Car From 150 Feet! ｜ MythBusters ｜ S7 E11 ｜ Full Episode [6Tr0zf03UoE].mkv')
media = instance.media_new('test/testvids/pass-this-on.webm')
#media = instance.media_new('test/testvids2/Juelz - Inferno [pbfHy45GG74].mp4')
player.set_media(media)
return_code = player.play()
print('return code ' + str(return_code)) # seems to always return zero

time.sleep(5)

player.stop()
media.release()
player.release()
