#!/bin/bash
# Daily run of the live warning feed for every basin in code/live/basins (about 15 s per basin), into runs/_live.
# The lab server's clock is US Pacific time: 17:00 there is 05:30-06:30 IST, so this cron line runs it every morning
# in India (add it with crontab -e, keeping the account's other entries):
#   0 17 * * * bash /home1/vineet/floodfm/code/server/run_live.sh >> /home1/vineet/floodfm/logs/live.log 2>&1
H=/home1/vineet/floodfm
cd $H/code
export PYTHONWARNINGS=ignore
echo "== live $(date '+%F %T')"
$H/env/bin/python live/run_live.py --out $H/runs/_live || echo "FAILED live"
