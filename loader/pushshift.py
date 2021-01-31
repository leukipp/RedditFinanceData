import os
import csv
import json
import time
import tqdm
import requests

from datetime import datetime


class Pushshift(object):
    def __init__(self, global_config, pushshift_config):
        self.global_config = global_config
        self.pushshift_config = pushshift_config

        # load global config
        with open(global_config) as f:
            config = json.load(f)
            self.subreddit = config['subreddit']
            self.data = config['pushshift']['data']

            self.last_run = {}
            self.end_run = {}

            now = int(datetime.utcnow().timestamp())
            for file_type in self.data.keys():
                self.last_run[file_type] = now
                self.end_run[file_type] = config['pushshift']['end_run']

        # load private config
        config = self.read_config()
        if 'last_run' in config and 'end_run' in config:
            for file_type in self.data.keys():
                self.last_run[file_type] = config['last_run'][file_type]
                self.end_run[file_type] = config['end_run'][file_type]
        self.url = 'https://api.pushshift.io/reddit/{}/search?limit=100&sort=desc&subreddit={}&after={}&before={}'

    def read_config(self):
        try:
            print('\nloading pushshift config...')
            with open(self.pushshift_config) as f:
                return json.load(f)
        except:
            return {}

    def write_config(self):
        with open(self.pushshift_config, 'w') as f:
            config = {
                'last_run': self.last_run,
                'end_run': self.end_run
            }
            json.dump(config, f, indent=4, sort_keys=True)

    def run(self):
        folder = os.path.join('data', self.subreddit)
        os.makedirs(folder, exist_ok=True)

        # download pushshift metadata from reddit
        for file_type, file_path in self.data.items():
            self.download(file_type, os.path.join(folder, file_path))

    def download(self, file_type, file_path):
        now = int(datetime.utcnow().timestamp())
        exists = os.path.exists(file_path)

        print(f'\ndownload {file_type}s before {datetime.fromtimestamp(self.last_run[file_type]).strftime("%Y-%m-%d %H:%M:%S")} to {file_path}\n')
        with open(file_path, 'a+', newline='') as f:
            writer = csv.writer(f, delimiter=';')

            # write csv header
            if not exists:
                writer.writerow({
                    'submission': ['submission', 'author', 'created', 'retrieved', 'removed'],
                    'comment': ['submission', 'comment', 'author', 'created', 'retrieved', 'removed']
                }[file_type])

            count = 0
            while True:
                # request data
                try:
                    url = self.url.format(file_type, self.subreddit, str(self.end_run[file_type]), str(self.last_run[file_type]))
                    result = requests.get(url).json()  # , headers={'User-Agent': 'python:https://github.com/leukipp/TODO:v0.0.1 (by /u/leukipp)'})
                except json.decoder.JSONDecodeError as e:
                    print(f'...request error {repr(e)}, retry')
                    time.sleep(1)
                    continue

                # validate result
                if 'data' not in result or not len(result['data']):
                    break

                # build csv
                rows = []
                for data in result['data']:
                    self.last_run[file_type] = data['created_utc'] - 1

                    # build row
                    try:
                        if file_type == 'submission' and 'selftext' in data and data['is_self']:
                            rows.append([
                                data['id'],
                                data['author'],
                                data['created_utc'],
                                data['retrieved_on'],
                                int(str(data['selftext']) == '[removed]')])
                        elif file_type == 'comment' and 'body' in data:
                            rows.append([
                                str(data['parent_id']).partition('_')[2],
                                data['id'],
                                data['author'],
                                data['created_utc'],
                                data['retrieved_on'],
                                int(str(data['body']) == '[removed]')])
                    except Exception as e:
                        print(f'...error {repr(e)}')

                    count += 1

                # update csv
                writer.writerows(rows)

                # update config
                self.write_config()

                # wait for next request
                time.sleep(0.35)

                # saved rows
                print(f'saved {count} {file_type}s after {datetime.fromtimestamp(self.last_run[file_type]).strftime("%Y-%m-%d %H:%M:%S")}')

            # saved all
            print(f'saved {count} {file_type}s')

        # update last and end run
        self.last_run[file_type] = now
        self.end_run[file_type] = now

        # update config
        self.write_config()