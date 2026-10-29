#!/bin/bash
# Run a command fully detached from the ssh session:  bash server/bg.sh <logfile> <command...>
log=$1; shift
cd /home1/vineet/floodfm
setsid nohup "$@" >> "$log" 2>&1 < /dev/null &
echo "started pid $! -> $log"
