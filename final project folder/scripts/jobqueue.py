"""Tiny GPU job queue: run every job in a jobs file, one at a time per worker slot.

    python scripts/jobqueue.py jobs.txt 0,1,1     # three slots: GPU0 once, GPU1 twice

Each line of jobs.txt: <run_name> <arguments for floodfm.train>.
A job is skipped when runs/<run_name>/results.json already exists, so the queue
can be stopped and restarted at any time. Logs go to logs/<run_name>.log.
"""
import os
import subprocess
import sys
import threading
import time

HOME = "/home1/vineet/floodfm"
jobs_file, slots = sys.argv[1], sys.argv[2].split(",")
lock = threading.Lock()


def next_job():
    with lock:
        for line in open(jobs_file):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            name, args = line.split(" ", 1)
            out = f"{HOME}/runs/{name}"
            if os.path.exists(f"{out}/results.json") or os.path.exists(f"{out}/.running"):
                continue
            os.makedirs(out, exist_ok=True)
            open(f"{out}/.running", "w").write(str(time.time()))
            return name, args, out
    return None


def worker(gpu):
    while True:
        job = next_job()
        if job is None:
            return
        name, args, out = job
        cmd = f"cd {HOME}/code && {HOME}/env/bin/python -m floodfm.train {args} --out {out}"
        env = dict(os.environ, CUDA_VISIBLE_DEVICES=gpu, HF_HOME=f"{HOME}/hf", PYTHONWARNINGS="ignore")
        t = time.time()
        with open(f"{HOME}/logs/{name}.log", "w") as log:
            rc = subprocess.call(cmd, shell=True, stdout=log, stderr=subprocess.STDOUT, env=env)
        os.remove(f"{out}/.running")
        with lock:
            open(f"{HOME}/logs/queue.log", "a").write(
                f"{time.strftime('%H:%M:%S')} gpu{gpu} {name} rc={rc} {time.time()-t:.0f}s\n")


threads = [threading.Thread(target=worker, args=(g,)) for g in slots]
for i, th in enumerate(threads):
    th.start()
    time.sleep(20 * (i > 0))  # stagger start-up (model downloads, cache warm-up)
for th in threads:
    th.join()
open(f"{HOME}/logs/queue.log", "a").write(f"{time.strftime('%H:%M:%S')} QUEUE DONE {jobs_file}\n")
