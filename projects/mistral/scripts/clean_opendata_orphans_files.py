from pathlib import Path
from datetime import datetime
from restapi.connectors import sqlalchemy
from restapi.utilities.logs import log

db = sqlalchemy.get_instance()
opendata_dir = Path("/opendata")
for f in opendata_dir.iterdir():
    if f.is_file():
        # check if is a tmp file and has passed the grace period
        if f.suffix == ".tmp":
            log.info(
                "temp file {} created on {} has passed the grace period and has been deleted",
                f,
                datetime.fromtimestamp(f.stat().st_mtime),
            )
            f.unlink()
            continue
        # check if it is an orphan file
        file_object = db.FileOutput.query.filter_by(
            filename=f.name
        ).first()
        if not file_object:
            log.info(
                "output file {} without a db entry and created on {} has passed the grace period and has been deleted",
                f,
                datetime.fromtimestamp(f.stat().st_mtime),
            )
            f.unlink()
