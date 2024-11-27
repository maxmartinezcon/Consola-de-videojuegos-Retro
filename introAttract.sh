#!/bin/bash
export DISPLAY=:0
export PULSE_SERVER=unix:/run/user/$(id -u han)/pulse/native
export XDG_RUNTIME_DIR=/run/user/$(id -u han)
pulseaudio --check || pulseaudio --start
/usr/bin/mpv --fullscreen --ao=pulse /home/han/gamecube_mp3.mp4
startx
/home/han/attract/attract

