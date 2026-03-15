"""python -m notify [--date YYYY-MM-DD]"""

import argparse

from notify.mattermost import main

parser = argparse.ArgumentParser(description="Send daily report to Mattermost")
parser.add_argument("--date", help="Report date (default: latest)")
args = parser.parse_args()
main(date=args.date)
