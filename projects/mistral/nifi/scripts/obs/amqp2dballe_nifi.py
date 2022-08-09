import datetime
import errno
import os
import select
import sys

import dballe

# sys.stdout = open('out', 'w')
# sys.stderr = open('err', 'w')

# get the DEFAULT DSN
user = os.environ.get("ALCHEMY_USER")
pw = os.environ.get("ALCHEMY_PASSWORD")
host = os.environ.get("ALCHEMY_HOST")
port = os.environ.get("ALCHEMY_PORT")


DEFAULT_DSN = f"postgresql://{user}:{pw}@{host}:{port}/DBALLE"
# print("Connecting: " + DEFAULT_DSN, file=sys.stdout)


# network enabled report station
network_filter = sys.argv[1].lower().split()
print(network_filter)

try:
    # if it cannot connect to dballe an error is raised as the incoming file can be saved in error folder)
    db = dballe.DB.connect(DEFAULT_DSN)
except BaseException as exc:
    print(str(exc), file=sys.stderr)
    sys.exit(111)

importer = dballe.Importer("BUFR")

data_now = datetime.datetime.now()
data_max = data_now + datetime.timedelta(hours=int(sys.argv[2]))
data_min = data_now - datetime.timedelta(hours=int(sys.argv[3]))
print(data_max)
print(data_min)

flowfileout = "/tmp/discarded_messages.tmp"

while sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
    data = sys.stdin.buffer
    # mime = data[0:4]
    # mimeb = mime.decode('UTF-8') # BUFR
    # print(data)
    network_errors = None
    reftime_errors = None
    if data:
        with open(flowfileout, "wb") as discarded_msgs:
            importer = dballe.Importer("BUFR")
            exporter = dballe.Exporter("BUFR")
            try:
                with importer.from_file(data) as f:
                    count_messages = 0
                    for messages in f:
                        for msg in messages:
                            count_messages += 1
                            count_vars = 0
                            new_msg = dballe.Message("generic")

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

                            # print(msg.datetime, msg.report)
                            if msg.report not in network_filter:
                                network_errors = msg.report
                                # save the message to the file of discarded messages
                                count_vars += 1
                            if (dt is not None) and (
                                (dt < data_min) or (dt > data_max)
                            ):
                                reftime_errors = dt
                                # save the message to the file of discarded messages
                                count_vars += 1
                            # if there is a discarded message save it to the file
                            if count_vars > 0:
                                discarded_msgs.write(exporter.to_binary(new_msg))
                            # print(msg.report)
                            else:
                                with db.transaction() as tr:
                                    tr.import_messages(
                                        msg,
                                        overwrite=True,
                                        update_station=True,
                                        import_attributes=True,
                                    )
            except BaseException as exc:
                print(str(exc), file=sys.stderr)
                sys.exit(109)

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
    elif count_messages == 0:
        print("No messages found in the received file", file=sys.stderr)
        sys.exit(109)

    sys.exit(0)

if os.path.isfile(flowfileout):
    os.remove(flowfileout)

sys.stdout.close()
sys.stderr.close()
