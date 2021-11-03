import os
import select
import sys

import dballe

DEFAULT_DSN = sys.argv[1]

while sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
    data = sys.stdin.buffer
    if data:
        db = dballe.DB.connect(DEFAULT_DSN)
        importer = dballe.Importer("BUFR")
        with db.transaction() as tr:
            tr.import_messages(
                importer.from_file(data),
                overwrite=True,
                update_station=True,
                import_attributes=True,
            )
    sys.exit(0)

sys.stdout.close()
sys.stderr.close()
