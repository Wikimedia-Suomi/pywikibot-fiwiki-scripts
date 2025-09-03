#!/usr/bin/env python3
import bz2
import requests
import os
import hashlib
import urllib.parse
import time
import csv
from urllib.parse import urlparse
from collections import deque
import threading
import queue

# request throttling
__request_times = deque()
__throttle_lock = threading.Lock()

# download speed tracking (events: timestamp, bytes)
__speed_events = deque()
__speed_lock = threading.Lock()

# download count tracking (timestamps)
__download_events = deque()

class FilenameMatchError(Exception):
    """Custom exception for filename mismatch errors"""
    pass


def throttle_requests():
    """Block so that we never exceed 9 req/s and always sleep at least 0.05s."""
    with __throttle_lock:
        now = time.perf_counter()
        # drop any timestamps older than 1 second
        while __request_times and now - __request_times[0] >= 1.0:
            __request_times.popleft()
        # if we've already done 9 in the past second, wait just enough
        if len(__request_times) >= 9:
            to_wait = 1.0 - (now - __request_times[0])
            time.sleep(to_wait)
            now = time.perf_counter()
            while __request_times and now - __request_times[0] >= 1.0:
                __request_times.popleft()
        __request_times.append(now)
    # always sleep at least 0.05s
    time.sleep(0.05)


def get_wikimedia_image_url(filename):
    """
    Construct the full-resolution Wikimedia Commons image URL based on filename.
    """
    md5_filename = filename.replace(' ', '_').encode('utf-8')
    safe_filename = urllib.parse.quote(filename.replace(' ', '_'))
    md5_hash = hashlib.md5(md5_filename).hexdigest()
    return f"https://upload.wikimedia.org/wikipedia/commons/{md5_hash[0]}/{md5_hash[:2]}/{safe_filename}"


def download_image(url, output_dir, wikimedia_filename):
    """
    Download an image from the given URL and save it; track speed and count.
    """
    try:
        headers = {
            "User-Agent": "ImagehashBot/0.3 (https://fi.wikipedia.org/wiki/user:Zache; https://phabricator.wikimedia.org/T391020)"
        }
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        path = parsed_url.path.lstrip('/')
        local_dir = os.path.join(output_dir, domain, os.path.dirname(path))
        encoded_filename = os.path.basename(path)
        decoded_filename = urllib.parse.unquote(encoded_filename)

        if decoded_filename.replace('_',' ') != wikimedia_filename.replace('_',' '):
            raise FilenameMatchError(f"Mismatch: {wikimedia_filename} vs {decoded_filename}")

        save_path = os.path.join(local_dir, decoded_filename)
        if os.path.exists(save_path):
            print(f"File exists, skipping: {save_path}")
            return True

        save_path2 = os.path.join(f'/work/qvo8TB/zache/t/{local_dir}', decoded_filename)
        if os.path.exists(save_path2):
            print(f"File exists, skipping: {save_path}")
            return True

        # throttle before request
        throttle_requests()
        response = requests.get(url, stream=True, headers=headers)
        time.sleep(int(response.headers.get('retry-after','0')))

        if response.status_code != 200:
            print(f"Failed ({response.status_code}): {url}")
            if response.status_code == 404:
                time.sleep(1)
            else:
                time.sleep(10)
            return False

        os.makedirs(local_dir, exist_ok=True)
        total_bytes = 0
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=1024):
                if not chunk:
                    continue
                f.write(chunk)
                total_bytes += len(chunk)

        # record speed and count events
        now = time.perf_counter()
        with __speed_lock:
            # speed
            __speed_events.append((now, total_bytes))
            while __speed_events and now - __speed_events[0][0] > 60:
                __speed_events.popleft()
            times = [t for t,_ in __speed_events]
            bytes_list = [b for _,b in __speed_events]
            elapsed = times[-1] - times[0] if len(times)>1 else 0
            avg_speed = sum(bytes_list)/elapsed if elapsed>0 else 0
            # count
            __download_events.append(now)
            while __download_events and now - __download_events[0] > 60:
                __download_events.popleft()
            count = len(__download_events)
            avg_dps = count / elapsed if elapsed>0 else 0

        print(f"Downloaded: {save_path} ({total_bytes/1024:.1f} KB)")
        if elapsed>0:
            print(f"Avg speed (last {elapsed:.1f}s): {avg_speed/1024:.1f} KB/s")
        print(f"Avg downloads/s (last {elapsed:.1f}s): {avg_dps:.2f}")
        return True

    except Exception as e:
        print(f"Error downloading {url}: {e}")
        time.sleep(10)
        return False


def process_bz2_tsv_file(file_path, filename_column=0, output_dir="downloaded_images"):
    try:
        os.makedirs(output_dir, exist_ok=True)
        success_count = failure_count = 0

        # parallel setup
        NUM_WORKERS = 8
        q = queue.Queue(maxsize=1000)
        counts_lock = threading.Lock()

        def worker():
            nonlocal success_count, failure_count
            while True:
                item = q.get()
                if item is None:
                    q.task_done()
                    break
                ln, fn = item
                try:
                    print(f"Processing line {ln}: {fn}")
                    url = get_wikimedia_image_url(fn)
                    if download_image(url, output_dir, fn):
                        with counts_lock: success_count+=1
                    else:
                        with counts_lock: failure_count+=1
                except Exception as e:
                    print(f"Error on line {ln}: {e}")
                    with counts_lock: failure_count+=1
                print("-"*50)
                q.task_done()

        threads = []
        for _ in range(NUM_WORKERS):
            t = threading.Thread(target=worker, daemon=True)
            t.start()
            threads.append(t)

        with bz2.open(file_path, 'rt', encoding='utf-8') as f:
            reader = csv.reader(f, delimiter='\t', quotechar='"', escapechar='\\', doublequote=False)
            for i, fields in enumerate(reader,1):
                if len(fields)<=filename_column or not (fn:=fields[filename_column].strip()):
                    print(f"Line {i}: skip")
                    continue
                q.put((i, fn))

        q.join()
        for _ in threads: q.put(None)
        for t in threads: t.join()

        print(f"\nSummary: success={success_count}, failed={failure_count}")

    except Exception as e:
        print(f"Unexpected error: {e}")
        time.sleep(5)

if __name__ == "__main__":
# Syntax for filenames.tsv.bz2 is one filename per line in double quotes
#
# Example:
# "!!!...Pierrot_(1916)_-_Carlos_Bonvalot_(Museu_Nacional_de_Arte_Contemporânea).png"
# "!!!_(chk_chk_chk)_(9036034320).jpg"
# "!!!_Mdina_buildings_05.jpg"

    file_path = "/tmp/filenames.tsv.bz2"
    output_dir = "wikimedia_images"
    filename_column = 0
    process_bz2_tsv_file(file_path, filename_column, output_dir)
