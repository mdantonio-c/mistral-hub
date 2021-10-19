from pathlib import Path

import dballe
from mistral.services.dballe import BeDballe
from restapi.utilities.logs import log


def pp_quality_check_filter(input_file: Path, output_file: Path) -> None:
    log.info("Filter the output file with quality check filter")
    with open(input_file, "rb") as inf:
        with open(output_file, "wb") as outf:
            importer = dballe.Importer("BUFR")
            exporter = dballe.Exporter("BUFR")

            with importer.from_file(inf) as fp:
                for msgs in fp:
                    for msg in msgs:
                        new_msg = BeDballe.filter_messages(msg, quality_check=True)
                        if new_msg:
                            outf.write(exporter.to_binary(new_msg))
