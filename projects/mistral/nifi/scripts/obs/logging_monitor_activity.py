import random
import sys
import time
from pathlib import Path


class ConcurrencyWriting(Exception):
    """The script can't log because of writing concurrency"""


service_name = sys.argv[1]
alert_code = sys.argv[2]
logfilename = sys.argv[3]

data = sys.stdin.buffer
monitor_message = data.readline().decode("utf-8")
message_log = f'{alert_code} "{service_name}" - {monitor_message}'


logfile_dir = Path("/opt/nifi/nifi-current/logs/custom_logs")
# check if there isn't a lock file (means that the logging file can be written)
retries = 0
lockfile = Path(logfile_dir, logfilename + ".lock")
while retries < 3:
    if lockfile.is_file():
        # wait
        time.sleep(random.randint(30, 60))
        retries += 1
    else:
        # no concurrency writing on the file
        break

# check if after the retries the lock file has gone
if lockfile.is_file():
    raise ConcurrencyWriting(
        f"Concurrency writing: can't log {message_log} on {Path(logfile_dir, logfilename)}"
    )

# create the lockfile to prevent concurrency writing
open(lockfile, "w").close()

custom_logfile = Path(logfile_dir, logfilename)
is_logfile = custom_logfile.is_file()

with open(custom_logfile, "a" if is_logfile else "w") as f:
    if is_logfile:
        f.write("\n")

    f.write(message_log)

# delete the lockfile
lockfile.unlink()
