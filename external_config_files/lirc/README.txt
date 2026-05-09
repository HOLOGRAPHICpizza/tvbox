IR Remote control with LIRC

Useful reading:
https://www.digikey.com/en/maker/tutorials/2021/how-to-send-and-receive-ir-signals-with-a-raspberry-pi
https://www.instructables.com/Setup-IR-Remote-Control-Using-LIRC-for-the-Raspber/
https://www.huitsing.nl/irftdi/

Had to add these symlinks on Debian 13 to get the python lirc module working:
sudo ln -s /usr/lib/x86_64-linux-gnu/python3.12/dist-packages/lirc /usr/lib/python3/dist-packages/lirc
sudo ln -s /usr/lib/x86_64-linux-gnu/python3.12/dist-packages/lirc-setup /usr/lib/python3/dist-packages/lirc-setup

Included files:
ftdi__lirc_options.conf	- /etc/lirc/lirc_options.conf for FTDI USB
lircrc			- ~/.config/lircrc configuration for irexec
irexec.desktop		- ~/.config/autostart/irexec.desktop autostart irexec
pioneer_CU-HTV001.lircd.conf	- pioneer remote file, place in /etc/lirc/lircd.conf.d/
SYLVANIA.lircd.conf		- another remote file

