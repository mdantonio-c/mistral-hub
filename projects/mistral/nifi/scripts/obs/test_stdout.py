import datetime
import errno
import json
import os
import select
import sys

import dballe

# sys.stdout = open('out', 'w')
# sys.stderr = open('err', 'w')

# how to call this script in NiFi
# obs/amqp2dballe_nifi.py;${network_list};${dt_fore_hours};${dt_back_hours};${accumulation_dsn};${trange_for_accum_dsn}

### IMPORTANT NOTE
## Do not use print() function to output anything to stdout
## this will corrupt the outgoing JSON messages stream for accumulation data

# get the DEFAULT DSN
user = os.environ.get("ALCHEMY_USER")
pw = os.environ.get("ALCHEMY_PASSWORD")
host = os.environ.get("ALCHEMY_HOST")
port = os.environ.get("ALCHEMY_PORT")


DEFAULT_DSN = f"postgresql://{user}:{pw}@{host}:{port}/DBALLE"
# print("Connecting: " + DEFAULT_DSN, file=sys.stdout)
ACCUMULATION_DSN = None
trange_for_accum_dsn = None
if len(sys.argv) == 6:
    accumulation_dsn_name = sys.argv[4]
    ACCUMULATION_DSN = f"postgresql://{user}:{pw}@{host}:{port}/{accumulation_dsn_name}"
    # get the list of the timeranges for pluvio data who needs to be duplicated in the accumulation dballe
    trange_for_accum_dsn = sys.argv[5].split(";")


# network enabled report station
network_filter = sys.argv[1].lower().split()

try:
    # if it cannot connect to dballe an error is raised as the incoming file can be saved in error folder)
    db = dballe.DB.connect(DEFAULT_DSN)
except BaseException as exc:
    print(str(exc), file=sys.stderr)
    sys.exit(111)

accumulation_db = None
if ACCUMULATION_DSN:
    try:
        accumulation_db = dballe.DB.connect(ACCUMULATION_DSN)
    except BaseException as exc:
        # raise a warning at least for now
        print(
            f"Exception in connecting to the accumulation db {ACCUMULATION_DSN} : {str(exc)}"
        )

importer = dballe.Importer("BUFR")

# Get ingestion timestamp
ingestion_timestamp = datetime.datetime.now().isoformat() + "Z"

data_now = datetime.datetime.now()
data_max = data_now + datetime.timedelta(hours=int(sys.argv[2]))
data_min = data_now - datetime.timedelta(hours=int(sys.argv[3]))

flowfileout = "/tmp/discarded_messages.tmp"

while sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
    data = sys.stdin.buffer
    # mime = data[0:4]
    # mimeb = mime.decode('UTF-8') # BUFR
    # print(data)
    malformed_msg_errors = None
    network_errors = None
    reftime_errors = None
    if data:
        with open(flowfileout, "wb") as discarded_msgs:
            importer = dballe.Importer("BUFR")
            exporter = dballe.Exporter("BUFR")
            exporter_json = dballe.Exporter("JSON")
            with importer.from_file(data) as f:
                count_messages = 0
                for messages in f:
                    for msg in messages:
                        message_ok = True
                        # to check if the data needs to be duplicated in the accumulation db
                        need_accumulation_db = False
                        count_messages += 1
                        count_vars = 0
                        new_msg = dballe.Message("generic")

                        # check the correctness of the message
                        try:
                            new_msg.set_named("year", msg.get_named("year"))
                            new_msg.set_named("month", msg.get_named("month"))
                            new_msg.set_named("day", msg.get_named("day"))
                            new_msg.set_named("hour", msg.get_named("hour"))
                            new_msg.set_named("minute", msg.get_named("minute"))
                            new_msg.set_named("second", msg.get_named("second"))
                            new_msg.set_named("rep_memo", msg.report)
                            new_msg.set_named("longitude", int(msg.coords[0] * 10**5))
                            new_msg.set_named("latitude", int(msg.coords[1] * 10**5))
                            if msg.ident:
                                new_msg.set_named("ident", msg.ident)

                            # copy the data
                            for data in msg.query_data({"query": "attrs"}):
                                variable = data["variable"]
                                attrs = variable.get_attrs()
                                v = dballe.var(
                                    data["variable"].code,
                                    data["variable"].get(),
                                )
                                for a in attrs:
                                    v.seta(a)

                                new_msg.set(data["level"], data["trange"], v)
                                if trange_for_accum_dsn:
                                    # decode the timerange to check the timerange list for accumulation db
                                    trange = data["trange"]
                                    decoded_trange = (
                                        f"{trange.pind},{trange.p1},{trange.p2}"
                                    )
                                    if (
                                        data["variable"].code == "B13011"
                                        and decoded_trange in trange_for_accum_dsn
                                    ):
                                        need_accumulation_db = True

                            # copy the station data
                            for data in msg.query_station_data({"query": "attrs"}):
                                variable = data["variable"]
                                attrs = variable.get_attrs()
                                v = dballe.var(
                                    data["variable"].code,
                                    data["variable"].get(),
                                )
                                for a in attrs:
                                    v.seta(a)

                                new_msg.set(dballe.Level(), dballe.Trange(), v)

                            dt = datetime.datetime(
                                msg.get_named("year").get(),
                                msg.get_named("month").get(),
                                msg.get_named("day").get(),
                                msg.get_named("hour").get(),
                                msg.get_named("minute").get(),
                                msg.get_named("second").get(),
                            )
                        except BaseException as exc:
                            message_ok = False
                            malformed_msg_errors = str(exc)

                        if not message_ok:
                            # save the message to the file of discarded messages
                            count_vars += 1
                        # print(msg.datetime, msg.report)
                        if msg.report not in network_filter:
                            network_errors = msg.report
                            # save the message to the file of discarded messages
                            count_vars += 1
                        if (dt is not None) and ((dt < data_min) or (dt > data_max)):
                            reftime_errors = dt
                            # save the message to the file of discarded messages
                            count_vars += 1
                        # if there is a discarded message save it to the file
                        if count_vars > 0:
                            if message_ok:
                                discarded_msgs.write(exporter.to_binary(new_msg))
                            else:
                                # save the original message
                                discarded_msgs.write(exporter.to_binary(msg))
                        # print(msg.report)
                        else:
                            with db.transaction() as tr:
                                tr.import_messages(
                                    msg,
                                    overwrite=True,
                                    update_station=True,
                                    import_attributes=True,
                                )
                            if need_accumulation_db and accumulation_db:
                                # ingest the data also in the accumulation db
                                with accumulation_db.transaction() as tr:
                                    tr.import_messages(
                                        msg,
                                        overwrite=True,
                                        update_station=True,
                                        import_attributes=True,
                                    )

                                # Extract station information
                                station_name = None
                                station_hmsl = None
                                for st_data in msg.query_station_data(
                                    {"query": "attrs"}
                                ):
                                    if (
                                        st_data["variable"].code == "B01019"
                                    ):  # station name
                                        station_name = st_data["variable"].get()
                                    elif (
                                        st_data["variable"].code == "B07030"
                                    ):  # height above sea level
                                        station_hmsl = st_data["variable"].get()

                                # Create JSON records for accumulation data
                                for data_rec in msg.query_data({"query": "attrs"}):
                                    trange = data_rec["trange"]
                                    decoded_trange = (
                                        f"{trange.pind},{trange.p1},{trange.p2}"
                                    )

                                    # Only create JSON for accumulation data
                                    if (
                                        data_rec["variable"].code == "B13011"
                                        and decoded_trange in trange_for_accum_dsn
                                    ):
                                        level = data_rec["level"]

                                        record = {
                                            "ts": ingestion_timestamp,
                                            "station_name": station_name,
                                            "station_hmsl": (
                                                float(station_hmsl)
                                                if station_hmsl is not None
                                                else None
                                            ),
                                            "ident": (msg.ident if msg.ident else None),
                                            "network": msg.report,
                                            "lon": float(msg.coords[0]),
                                            "lat": float(msg.coords[1]),
                                            "date": dt.isoformat() + "Z",
                                            "timerange": int(trange.pind),
                                            "p1": int(trange.p1),
                                            "p2": int(trange.p2),
                                            "varcode": data_rec["variable"].code,
                                            "value": float(data_rec["variable"].get()),
                                            "level1": (
                                                int(level.ltype1)
                                                if level.ltype1
                                                else None
                                            ),
                                            "l1": (int(level.l1) if level.l1 else None),
                                            "level2": (
                                                int(level.ltype2)
                                                if level.ltype2
                                                else None
                                            ),
                                            "l2": (int(level.l2) if level.l2 else None),
                                        }

                                        # Write JSON to stdout
                                        json_line = json.dumps(
                                            record, ensure_ascii=False
                                        )
                                        print(json_line, file=sys.stdout)
                                        sys.stdout.flush()

    if network_errors:
        print(f"Not valid report Network: {network_errors}", file=sys.stderr)
        with open(flowfileout, "rb") as fileout:
            for m in fileout:
                sys.stdout.buffer.write(m)
        sys.exit(102)
    elif reftime_errors:
        print(f"Not valid report Time Ref: {reftime_errors}", file=sys.stderr)
        with open(flowfileout, "rb") as fileout:
            for m in fileout:
                sys.stdout.buffer.write(m)
        sys.exit(101)
    elif malformed_msg_errors:
        print(
            f"Not valid messages in this batch: {malformed_msg_errors}", file=sys.stderr
        )
        with open(flowfileout, "rb") as fileout:
            for m in fileout:
                sys.stdout.buffer.write(m)
        sys.exit(109)
    elif count_messages == 0:
        print("No messages found in the received file", file=sys.stderr)
        sys.exit(109)

    sys.exit(0)

if os.path.isfile(flowfileout):
    os.remove(flowfileout)

if os.path.isfile(tempaggr):
    os.remove(tempaggr)

sys.stdout.close()
sys.stderr.close()
