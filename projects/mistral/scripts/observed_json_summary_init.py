import os
import sys

import dballe
from mistral.services.arkimet import BeArkimet as arki_service
from mistral.services.dballe import BeDballe as dballe_service
from restapi.utilities.logs import log

# get all observed datasets
datasets = arki_service.get_obs_datasets(None, None)

# path to json_summary_file
json_summary = "/arkimet/config/arkimet_summary.json"

total_count = 0
# fill a temporary dballe with all observed data coming from arkimet
for d in datasets:
    e = dballe.DBExplorer()
    d_as_a_list = [d]
    temp_db = dballe_service.fill_db_from_arkimet(d_as_a_list, "")
    log.info(f"importing data from {d} dataset")
    with e.update() as updater:
        # Load existing json summary
        data_in_json_count = 0
        if os.path.exists(json_summary):
            with open(json_summary) as fd:
                updater.add_json(fd.read())
            for cur in e.query_summary_all({}):
                data_in_json_count += cur["count"]
        with temp_db.transaction() as tr:
            db_data_count = tr.query_data().remaining
            updater.add_db(tr)
    explorer_data_count = 0
    for cur in e.query_summary_all({}):
        explorer_data_count += cur["count"]
    log.info(
        f"Data coming from arkimet: {db_data_count}, Data already in json: {data_in_json_count}, Data in explorer at the end of operation: {explorer_data_count}"
    )
    newly_imported_data_count = explorer_data_count - data_in_json_count
    log.info(
        f"Succesfully imported in explorer {newly_imported_data_count} out of {db_data_count}"
    )
    total_count += newly_imported_data_count
    # Write out
    log.info("Exporting in JSON ...")
    with open(json_summary, "wt") as fd:
        fd.write(e.to_json())
    log.info("#####################################")

check_explorer = dballe.DBExplorer()
with check_explorer.update() as updater:
    with open(json_summary) as fd:
        updater.add_json(fd.read())
data_in_final_json_count = 0
for cur in check_explorer.query_summary_all({}):
    data_in_final_json_count += cur["count"]
log.info(f"{data_in_final_json_count} saved in JSON out of {total_count} processed")
log.info("######### DONE #########")
