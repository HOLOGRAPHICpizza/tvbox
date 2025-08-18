import gpiozero
import time

current_channel = 0

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
    gpiozero.LED('GPIO20'), # DIGIT 1
    gpiozero.LED('GPIO21')  # DIGIT 2
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

def set_segments(numeral: str):
    for segment in range(7):
        if DIGIT_SEGMENTS[numeral][segment]:
            SEGMENT_PINS[segment].on()
        else:
            SEGMENT_PINS[segment].off()


def seven_seg_loop():
    first_digit = True
    while True:
        #num_str = str(current_channel).rjust(2, ' ')
        num_str = str(int(time.time()))[-2:]

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

if __name__ == '__main__':
    seven_seg_loop()
