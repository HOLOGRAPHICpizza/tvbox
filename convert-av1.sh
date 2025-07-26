#!/bin/bash

mkdir orig

while read -r line; do
  ffmpeg -i "$line" -vf scale=-1:720 -c:v libx265 -c:a copy "${line%.*}_720p.mkv"
  basename=$(basename "$line")
  mv "$line" "orig/$basename"
done < "av1.txt"