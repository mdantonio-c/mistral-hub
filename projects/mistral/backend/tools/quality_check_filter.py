import dballe
from mistral.services.dballe import BeDballe
from restapi.utilities.logs import log


def pp_quality_check_filter(input, output):
    log.info("Filter the output file with quality check filter")
    with open(input, "rb") as input_file:
        with open(output, "wb") as output_file:
            importer = dballe.Importer("BUFR")
            exporter = dballe.Exporter("BUFR")

            with importer.from_file(input_file) as fp:
                for msgs in fp:
                    for msg in msgs:
                        new_msg = BeDballe.filter_messages(msg, quality_check=True)
                        if new_msg:
                            output_file.write(exporter.to_binary(new_msg))
