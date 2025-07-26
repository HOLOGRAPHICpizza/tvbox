import os
import subprocess

MEDIA_DIR = '/home/michael/tvbox_media'

for dirpath, dirnames, files in os.walk(MEDIA_DIR):
    for name in files:
        lowname = name.lower()
        if (lowname.endswith(".avi")
                or lowname.endswith(".mpg")
                or lowname.endswith(".mpeg")
                or lowname.endswith(".asf")
                or lowname.endswith(".wmv")
                or lowname.endswith(".mp4")
                or lowname.endswith(".mov")
                or lowname.endswith(".3gp")
                or lowname.endswith(".ogm")
                or lowname.endswith(".mkv")
                or lowname.endswith(".m4v")
                or lowname.endswith(".webm")):

            fullname = os.path.join(dirpath, name)
            result = subprocess.run(['/usr/bin/ffprobe', fullname],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
                                text=True,
                                check=True)

            if 'Video: av1' in result.stdout:
                print(fullname)