import os

import dballe
from mistral.services.arkimet import BeArkimet as arki_service
from mistral.services.dballe import BeDballe as dballe_service
from mistral.services.sqlapi_db_manager import SqlApiDbManager
from restapi.connectors import sqlalchemy
from restapi.utilities.logs import log

user = os.environ.get("ALCHEMY_USER")
pw = os.environ.get("ALCHEMY_PASSWORD")
host = os.environ.get("ALCHEMY_HOST")
engine = os.environ.get("ALCHEMY_DBTYPE")
port = os.environ.get("ALCHEMY_PORT")

# get the list of dsn from the db
alchemy_db = sqlalchemy.get_instance()
license_groups = alchemy_db.GroupLicense.query.filter_by().all()
dsn_list = []
dsn_list.extend(
    x.dballe_dsn
    for x in license_groups
    if x.dballe_dsn and x.dballe_dsn not in dsn_list
)
datasets_to_filter = [
    arki_service.from_network_to_dataset(x) for x in dballe_service.MAPS_NETWORK_FILTER
]
license_groups_need_filtering = []
for ds in datasets_to_filter:
    group_lic = SqlApiDbManager.get_license_group(alchemy_db, [ds])
    license_groups_need_filtering.append(group_lic.name)

log.debug("groups needing filtering: {}", license_groups_need_filtering)

for dsn in dsn_list:
    log.debug("summary for {}", dsn)
    DB = dballe.DB.connect(f"{engine}://{user}:{pw}@{host}:{port}/{dsn}")
    # check if there is also an associated dsn for mobile stations
    try:
        mobile_dsn = f"{dsn}_MOBILE"
        mobile_db = dballe.DB.connect(
            f"{engine}://{user}:{pw}@{host}:{port}/{mobile_dsn}"
        )
    except OSError:
        log.debug("{} dsn for mobile station data does not exists", dsn)
        mobile_db = None

    log.debug("Extracting dballe summary...")

    total_count = 0
    explorer = dballe.DBExplorer()

    # create the explorer from the db
    with explorer.update() as updater:
        with DB.transaction() as tr:
            updater.add_db(tr)
        # if exists add also the corresponding dsn for mobile stations
        if mobile_db:
            with mobile_db.transaction() as tr:
                updater.add_db(tr)

    # count the total of elements
    for cur in explorer.query_summary_all({}):
        total_count += cur["count"]

    # check if the dsn contains a single group of licenses
    dsn_license_group_list = [
        x.name for x in alchemy_db.GroupLicense.query.filter_by(dballe_dsn=dsn).all()
    ]
    if len(dsn_license_group_list) == 1:
        # path to json_summary_file
        complete_json_summary = "{}_{}.json".format(
            dballe_service.DBALLE_JSON_SUMMARY_PATH,
            dsn_license_group_list[0].replace(" ", "_"),
        )
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

        # check if the dsn needs a filtered summary (multimodel use case)
        if dsn_license_group_list[0] in license_groups_need_filtering:
            filtered_json_summary = "{}_{}.json".format(
                dballe_service.DBALLE_JSON_SUMMARY_PATH_FILTERED,
                dsn_license_group_list[0].replace(" ", "_"),
            )

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
    else:
        # case of dsn containing different license groups
        for lg in dsn_license_group_list:
            # path to json_summary_file
            complete_json_summary = "{}_{}.json".format(
                dballe_service.DBALLE_JSON_SUMMARY_PATH_FILTERED, lg.replace(" ", "_")
            )
            # retrieve networks of the license group
            dataset_list = SqlApiDbManager.retrieve_dataset_by_license_group(
                alchemy_db, lg
            )
            net_list = []
            for ds in dataset_list:
                nets = arki_service.from_dataset_to_networks(ds)
                net_list.extend(n for n in nets)
            # create a subset of the explorer
            subset_explorer = dballe.DBExplorer()
            for n in net_list:
                explorer.set_filter({"rep_memo": n})
                with subset_explorer.update() as updater:
                    updater.add_explorer(explorer)
            log.debug(
                "license: {},nets for license: {},nets in explorer {}",
                lg,
                net_list,
                subset_explorer.reports,
            )
            # write the filtered explorer to the file
            with open(complete_json_summary, "wt") as fd:
                fd.write(subset_explorer.to_json())

        # at the moment we don't need a filtered summary in this use case as the only network to filter is the multimodel one which is in an open dsn (so doesn't match with this use case)
        # so the complete summary is already the filtered one as it does not contain networks considered to be filtered
