from gpiozero import Button
from time import sleep

chan_up = Button('GPIO17', pull_up=True, bounce_time=0.05)
chan_down = Button('GPIO27', pull_up=True, bounce_time=0.05)
btn_2 = Button('GPIO22', pull_up=True, bounce_time=0.05)
btn_3 = Button('GPIO10', pull_up=True, bounce_time=0.05)

def chan_up_pressed():
    print('chan_up')

def chan_down_pressed():
    print('chan_down')

def btn_2_pressed():
    print('btn_2')

def btn_3_pressed():
    print('btn_3')

chan_up.when_pressed = chan_up_pressed
chan_down.when_pressed = chan_down_pressed
btn_2.when_pressed = btn_2_pressed
btn_3.when_pressed = btn_3_pressed

while True:
    sleep(1)

