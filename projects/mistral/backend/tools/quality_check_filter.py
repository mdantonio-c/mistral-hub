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
                        count_vars = 0
                        new_msg = dballe.Message("generic")

                        new_msg.set_named("year", msg.get_named("year"))
                        new_msg.set_named("month", msg.get_named("month"))
                        new_msg.set_named("day", msg.get_named("day"))
                        new_msg.set_named("hour", msg.get_named("hour"))
                        new_msg.set_named("minute", msg.get_named("minute"))
                        new_msg.set_named("second", msg.get_named("second"))
                        new_msg.set_named("rep_memo", msg.report)
                        new_msg.set_named("longitude", int(msg.coords[0] * 10 ** 5))
                        new_msg.set_named("latitude", int(msg.coords[1] * 10 ** 5))
                        if msg.ident:
                            new_msg.set_named("ident", msg.ident)
                        for data in msg.query_data({"query": "attrs"}):
                            variable = data["variable"]
                            attrs = variable.get_attrs()
                            is_ok = BeDballe.data_qc(attrs)
                            v = dballe.var(
                                data["variable"].code, data["variable"].get()
                            )

                            if not is_ok:
                                # the message has not passed quality check controls
                                continue

                            new_msg.set(data["level"], data["trange"], v)
                            count_vars += 1

                        for data in msg.query_station_data({"query": "attrs"}):
                            variable = data["variable"]
                            attrs = variable.get_attrs()
                            v = dballe.var(
                                data["variable"].code, data["variable"].get()
                            )
                            for a in attrs:
                                v.seta(a)

                            new_msg.set(dballe.Level(), dballe.Trange(), v)

                        if count_vars > 0:
                            output_file.write(exporter.to_binary(new_msg))
