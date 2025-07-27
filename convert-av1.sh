#!/bin/bash

mkdir orig

while read -r line; do
  ffmpeg -nostdin -loglevel warning -i "$line" -vf scale=-1:720 -c:v libx265 -c:a copy "${line%.*}_720p.mkv"
  #ffmpeg -nostdin -loglevel warning -i "$line" -c:v libx265 -c:a copy "${line%.*}_h265.mkv"
  basename=$(basename "$line")
  mv "$line" "orig/$basename"
done < "av1.txt"