import os

import dballe
from mistral.services.dballe import BeDballe as dballe_service
from restapi.utilities.logs import log

user = os.environ.get("ALCHEMY_USER")
pw = os.environ.get("ALCHEMY_PASSWORD")
host = os.environ.get("ALCHEMY_HOST")
engine = os.environ.get("ALCHEMY_DBTYPE")
port = os.environ.get("ALCHEMY_PORT")

DB = dballe.DB.connect(f"{engine}://{user}:{pw}@{host}:{port}/DBALLE")


# path to json_summary_file
complete_json_summary = dballe_service.DBALLE_JSON_SUMMARY_PATH
filtered_json_summary = dballe_service.DBALLE_JSON_SUMMARY_PATH_FILTERED

total_count = 0
explorer = dballe.DBExplorer()

# create the explorer from the db
with explorer.update() as updater:
    with DB.transaction() as tr:
        updater.add_db(tr)
# count the total of elements
for cur in explorer.query_summary_all({}):
    total_count += cur["count"]

# export the complete explorer to the json file
with open(complete_json_summary, "wt") as fd:
    fd.write(explorer.to_json())

# check that the json summary is complete
check_count = 0
checking_explorer = dballe.DBExplorer()
with checking_explorer.update() as updater:
    # Load the json summary
    with open(complete_json_summary) as fd:
        updater.add_json(fd.read())
for cur in checking_explorer.query_summary_all({}):
    check_count += cur["count"]

if total_count != check_count:
    log.error("Problems in creating the dballe json summary")

# create the filtered json summary
all_nets = explorer.all_reports
filtered_explorer = dballe.DBExplorer()
for net in all_nets:
    if net not in dballe_service.MAPS_NETWORK_FILTER:
        explorer.set_filter({"rep_memo": net})
        # add the filtered explorer to the general one
        with filtered_explorer.update() as updater:
            updater.add_explorer(explorer)

# export the filtered explorer to a json file
with open(filtered_json_summary, "wt") as fd:
    fd.write(filtered_explorer.to_json())
