# this is the 2nd file in the tvbox launch chain
# ran by tvbox
# runs tvbox.py

# maximize window
sleep 2
wmctrl -r 'tvboxterm' -b add,maximized_vert,maximized_horz

# launch tvbox.py
python3 "$TVBOX_DIR/tvbox.py" "$TVBOX_CHANNELS_DIR" 2>&1 | tee "$TVBOX_LOG"

# keep the terminal open
if pgrep -f -a "bash -i"; then # is bash -i already running?
	: # no-op
else
	if [ $TVBOX_DEBUG -eq 1 ]; then
		bash -i
	fi
fi
