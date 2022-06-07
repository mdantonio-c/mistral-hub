import os
import select
import sys

import dballe

# get the DEFAULT DSN
user = os.environ.get("ALCHEMY_USER")
pw = os.environ.get("ALCHEMY_PASSWORD")
host = os.environ.get("ALCHEMY_HOST")
port = os.environ.get("ALCHEMY_PORT")

DEFAULT_DSN = f"postgresql://{user}:{pw}@{host}:{port}/DBALLE"


while sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
    data = sys.stdin.buffer
    if data:
        try:
            db = dballe.DB.connect(DEFAULT_DSN)
            importer = dballe.Importer("BUFR")
            with db.transaction() as tr:
                tr.import_messages(
                    importer.from_file(data),
                    overwrite=True,
                    update_station=True,
                    import_attributes=True,
                )
        except BaseException as exc:
            print(str(exc))
            sys.exit(109)
    sys.exit(0)

sys.stdout.close()
sys.stderr.close()
