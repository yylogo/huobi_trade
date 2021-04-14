#!/bin/bash
export LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH

if [ "$1" == "-t" ]; then
    python3 -B main.py -t
else
    python3 -B main.py
fi
