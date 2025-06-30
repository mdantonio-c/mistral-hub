import itertools
import math
import subprocess
import tempfile
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import arkimet as arki
import dateutil
import dballe
import wreport
from mistral.exceptions import (
    EmptyOutputFile,
    InvalidFiltersException,
    JoinObservedExtraction,
    NetworkNotInLicenseGroup,
    UnAuthorizedUser,
    UnexistingLicenseGroup,
    WrongDbConfiguration,
)
from mistral.services.arkimet import BeArkimet as arki_service
from mistral.services.sqlapi_db_manager import SqlApiDbManager
from restapi.connectors import sqlalchemy
from restapi.env import Env
from restapi.utilities.logs import log


class BeDballe:
    MAPS_NETWORK_FILTER = []  # ["multim-forecast"]
    explorer = None
    # number of days after which data pass in Arkimet
    LASTDAYS = Env.get_int("LASTDAYS", 10)
    AGGREGATIONS_TRANGES = Env.get("AGGREGATIONS_TRANGES", "").split(";")
    AGGREGATIONS_DSN = Env.get("AGGREGATIONS_DSN", "")

    # base path to json file where metadata of observed data in arkimet are stored
    # the complete path name is  EX. /arkimet/config/dballe_summary_<license group name>.json
    SUMMARY_PATH = Path("/arkimet/config")
    ARKI_JSON_SUMMARY_PATH = "/arkimet/config/arkimet_summary"
    ARKI_JSON_SUMMARY_PATH_FILTERED = "/arkimet/config/arkimet_summary_filtered"
    DBALLE_JSON_SUMMARY_PATH = "/arkimet/config/dballe_summary"
    DBALLE_JSON_SUMMARY_PATH_FILTERED = "/arkimet/config/dballe_summary_filtered"

    # dballe codes for quality check attributes to consider for quality check filters
    QC_CODES = ["B33007", "B33192"]

    ################################################
    # CONSTANTS USEFUL FOR MESSAGES AND SIZE COUNT #
    ################################################

    # This dictionary is used to identify when the current cursor is the reference one.
    # This becomes necessary when a different method of size counting is required, as explained later.
    IS_REF_CUR_CHECKS = [
        ("trange", "ref_trange"),
        ("var", "ref_var"),
        ("level", "ref_level"),
    ]

    # This dictionary is used to identify newly covered attributes by the cursor when it is not the reference cursor.
    # This becomes necessary when a different method of size counting is required, as explained later.
    NEW_ATTR_COVERED_CHECKS = [
        ("pindicator", "tranges_covered", "pind"),  # is_a_new_trange_attr_type
        ("p1", "tranges_covered", "p1"),  # is_a_new_trange_attr_p1_
        ("p2", "tranges_covered", "p2"),  # is_a_new_trange_attr_p2
        ("leveltype1", "levels_covered", "ltype1"),  # is_a_new_level_l1_attr_type
        ("l1", "levels_covered", "l1"),  # is_a_new_level_l1_attr_value
        ("leveltype2", "levels_covered", "ltype2"),  # is_a_new_level_l2_attr_type
        ("l2", "levels_covered", "l2"),  # is_a_new_level_l2_attr_value
    ]

    # This dictionary is used to retrieve additional bits for newly covered attributes when a different size
    # counting method is needed (as explained later).
    NEW_ATTR_BITS = {
        "pindicator": 26,  # bits_attr_encoding += 10 ; bits_section_3 += 16 (i.e.: 2 Bytes)
        "p1": 47,  # bits_attr_encoding += 31 ; bits_section_3 += 16 (i.e.: 2 Bytes)
        "p2": 47,  # bits_attr_encoding += 31 ; bits_section_3 += 16 (i.e.: 2 Bytes)
        "leveltype1": 26,  # bits_attr_encoding += 10 ; bits_section_3 += 16 (i.e.: 2 Bytes)
        "l1": 47,  # bits_attr_encoding += 31 ; bits_section_3 += 16 (i.e.: 2 Bytes)
        "leveltype2": 47,  # bits_attr_encoding += 31 ; bits_section_3 += 16 (i.e.: 2 Bytes)
        "l2": 47,  # bits_attr_encoding += 31 ; bits_section_3 += 16 (i.e.: 2 Bytes)
    }

    LEVEL_ATTR_CUR_KEYS = ("l1", "leveltype2", "l2")
    LEVEL_AND_TRANGES_CUR_KEYS = (
        "pindicator",
        "p1",
        "p2",
        "leveltype1",
        "l1",
        "leveltype2",
        "l2",
    )

    # STANDARD BITS FOR BUFR MESSAGES' SIZE COUNT
    # Explanation of fixed byte/bits values used later for size count.
    # The analysis was done by analyzing the contents of many BUFR files;
    # BUFR messages are divided into different sections covering descriptors, attribute encoding, etc.

    # STANDARD_FIXED_BITS = 45 extra fixed bytes for each message:
    # 8 "general header" + 22 "SECTION_1" + 7 "SECTION_3" + 4 "SECTION_4" + 4 "SECTION_5".
    # The "* 8" is for "byte -> bit" conversion.
    STANDARD_FIXED_BITS = 360  # = 45 * 8

    # STANDARD_SECTION_3_BITS -> 15 attributes of the average message, each carry 2 extra bytes in "SECTION_3"
    # (include descriptors of various attributes). In "SECTION_3" there is also 1 extra byte,
    # for unknown reasons. The "* 8" is for byte -> bit conversion.
    # N.B.: If we considered the (often present) attribute "barometer height above sea level," it should be:
    # STANDARD_SECTION_3_BITS = 264 = (16 * 2 + 1) * 8
    STANDARD_SECTION_3_BITS = 248  # = (15 * 2 + 1) * 8

    # STANDARD_ATTR_ENCODING_BITS = 573 -> these are the bits for encoding anagraphic attributes
    # for an average message in "SECTION_4".
    STANDARD_ATTR_ENCODING_BITS = 573

    @staticmethod
    def get_db_type(date_min=None, date_max=None):
        now = datetime.utcnow()
        days_back = BeDballe.LASTDAYS - 1
        # the following checks if the request is at least 5 minutes before the start of the cron
        # of the migration from dballe to arkimet "start_dballe2arkimet.sh" (it is currently set at 2:15 AM)
        if now.hour < 2 or (now.hour == 2 and now.minute < 10):
            days_back += 1
        dballe_data_cutoff = (now - timedelta(days=days_back)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        if date_min:
            date_min_before_cutoff = date_min < dballe_data_cutoff
        else:
            # if there is not a datemin for sure the dbtype will be arkimet or mixed
            date_min_before_cutoff = True
        if date_max:
            date_max_before_cutoff = date_max < dballe_data_cutoff
        else:
            # if there is not datemax for sure the dbtype will be dballe or mixed
            date_max_before_cutoff = False
        if date_min_before_cutoff:
            if date_max_before_cutoff:
                db_type = "arkimet"
            else:
                db_type = "mixed"
        else:
            db_type = "dballe"

        # the following is the correct way to obtain the db (today - BeDballe.LASTDAYS in the previous method enters the case of mixed db)
        # but with the previous method is covered the special case of the hours between midnight and the actual migration from dballe to arkimet

        # today = datetime.utcnow().date()
        # first_arkimet_day = today - timedelta(days=BeDballe.LASTDAYS)
        # if date_min:
        #     min_day = date_min.date()
        # else:
        #     # if there is not a datemin for sure the dbtype will be arkimet or mixed
        #     min_day = first_arkimet_day
        #
        # if date_max:
        #     max_day = date_max.date()
        # else:
        #     # if there is not datemax for sure the dbtype will be dballe or mixed
        #     max_day = first_arkimet_day + timedelta(days=1)
        #
        # if min_day <= first_arkimet_day:
        #     if max_day > first_arkimet_day:
        #         db_type = "mixed"
        #     else:
        #         db_type = "arkimet"
        # else:
        #     db_type = "dballe"

        return db_type

    @staticmethod
    def split_reftimes(date_min, date_max):
        refmax_dballe = None
        refmin_dballe = None
        refmax_arki = None
        refmin_arki = None
        if date_max:
            refmax_dballe = date_max
        if date_min:
            refmin_arki = date_min
        now = datetime.utcnow()
        days_back = BeDballe.LASTDAYS - 1
        # the following checks if the request is at least 5 minutes before the start of the cron
        # of the migration from dballe to arkimet "start_dballe2arkimet.sh" (it is currently set at 2:15 AM).
        if now.hour < 2 or (now.hour == 2 and now.minute < 10):
            days_back += 1
        refmin_dballe = (now - timedelta(days=days_back)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        refmax_arki = refmin_dballe - timedelta(minutes=1)

        return refmax_dballe, refmin_dballe, refmax_arki, refmin_arki

    @staticmethod
    def check_access_authorization(user, g_license_name, dataset_name, dsn_subset=True):
        alchemy_db = sqlalchemy.get_instance()
        dataset_subset = []
        # 1. user is authorized to see data from that license group
        # (is open or at least one of his authorized dataset comes from the group)
        group_license = alchemy_db.GroupLicense.query.filter_by(
            name=g_license_name
        ).first()
        if not group_license:
            raise UnexistingLicenseGroup(
                "The selected group of license does not exists"
            )
        # check if the license group is open
        if not group_license.is_public:
            if not user:
                raise UnAuthorizedUser(
                    "to access not open datasets the user has to be logged"
                )
            else:
                auth_datasets = []
                auth_datasets_dic = SqlApiDbManager.get_datasets(
                    alchemy_db, user, category="OBS", group_license=g_license_name
                )
                for d in auth_datasets_dic:
                    auth_datasets.append(d["id"])
                if not auth_datasets:
                    raise UnAuthorizedUser(
                        "the user is not authorized to access datasets from the selected license group"
                    )
                if dsn_subset:
                    # check if the user is authorized to all datasets in
                    # the DSN corresponding to the license group
                    all_datasets = SqlApiDbManager.retrieve_dataset_by_dsn(
                        alchemy_db, group_license.dballe_dsn
                    )
                else:
                    all_datasets = SqlApiDbManager.retrieve_dataset_by_license_group(
                        alchemy_db, g_license_name
                    )
                log.debug(
                    "all datasets: {} by dsn={}, authorized datasets: {}",
                    all_datasets,
                    dsn_subset,
                    auth_datasets,
                )
                if set(auth_datasets) != set(all_datasets):
                    dataset_subset = [elem for elem in auth_datasets]
        # 2. if a network is requested check if belongs to the selected license group
        if dataset_name:
            ds_group_license = SqlApiDbManager.get_license_group(
                alchemy_db, [dataset_name]
            )
            if ds_group_license.name != group_license.name:
                raise NetworkNotInLicenseGroup(
                    "The selected network and the selected license group does not match"
                )
        return group_license, dataset_subset

    @staticmethod
    def build_arkimet_query(
        datemin=None,
        datemax=None,
        network=None,
        bounding_box=None,
        dballe_query=None,
        all_dballe_queries=None,
        fields=None,
        license_group=None,
    ):
        if isinstance(datemin, datetime):
            datemin_str = datemin.strftime("%Y-%m-%d %H:%M:%S")
            datemin = datemin_str

        if isinstance(datemax, datetime):
            datemax_str = datemax.strftime("%Y-%m-%d %H:%M:%S")
            datemax = datemax_str

        arkimet_query = ""
        if datemin:
            arkimet_query = "reftime: >={datemin},<={datemax};".format(
                datemin=datemin, datemax=datemax
            )
        if network:
            arkimet_query += f"product: BUFR:t = {network[0]}"
            if len(network) > 1:
                for i in network[1:]:
                    arkimet_query += f" or  BUFR:t = {i}"
            arkimet_query += ";"
        if dballe_query or all_dballe_queries:
            # improve the query adding stations
            explorer = BeDballe.build_explorer(
                "arkimet", license_group=license_group, network_list=network
            )
            # create a list of station details
            station_list = []
            # populate the station list.
            # If there is all_dballe_queries do an iteration to populate the list
            if dballe_query:
                for cur in explorer.query_summary_all(dballe_query):
                    el = {}
                    el["lat"] = cur["lat"]
                    el["lon"] = cur["lon"]
                    station_list.append(el)
            elif all_dballe_queries:
                for q in all_dballe_queries:
                    dballe_query = {}
                    for k, v in zip(fields, q):
                        dballe_query[k] = v
                    for cur in explorer.query_summary_all(dballe_query):
                        el = {}
                        el["lat"] = cur["lat"]
                        el["lon"] = cur["lon"]
                        station_list.append(el)
            if station_list:
                arkimet_query += "area: GRIB:lat={}, lon={}".format(
                    str(station_list[0]["lat"]).replace(".", ""),
                    str(station_list[0]["lon"]).replace(".", ""),
                )
                if len(station_list) > 1:
                    for e in station_list[1:]:
                        query_to_add = " or GRIB:lat={}, lon={}".format(
                            str(e["lat"]).replace(".", ""),
                            str(e["lon"]).replace(".", ""),
                        )
                        if query_to_add not in arkimet_query:
                            arkimet_query += query_to_add
            else:
                # if there is no station list it means there are no data for this query
                return None
        if bounding_box:
            if arkimet_query:
                if "area:" not in arkimet_query:
                    arkimet_query += "area: "
                else:
                    arkimet_query += " or "
            else:
                arkimet_query = "area: "
            arkimet_query += "bbox intersects POLYGON(({lonmin} {latmin},{lonmin} {latmax},{lonmax} {latmax}, {lonmax} {latmin}, {lonmin} {latmin}))".format(
                lonmin=bounding_box["lonmin"],
                latmin=bounding_box["latmin"],
                lonmax=bounding_box["lonmax"],
                latmax=bounding_box["latmax"],
            )
        return arkimet_query

    @staticmethod
    def build_explorer(db_type, license_group=None, network_list=None):
        # Patch provvisoria per far funzionare le mappe, in attesa di fixare per bene il summary filtered (che non
        # dovrebbe piùà servire
        need_filtered = False
        if network_list:
            # match_nets = next(
            #     (net for net in network_list if net in BeDballe.MAPS_NETWORK_FILTER),
            #     None,
            # )
            # if match_nets:
            #     need_filtered = False
            if not license_group:
                alchemy_db = sqlalchemy.get_instance()
                license_group = SqlApiDbManager.get_license_group(
                    alchemy_db, network_list
                )
        if not license_group:
            raise UnexistingLicenseGroup
        # log.debug("filtered {}", need_filtered)
        explorer = dballe.DBExplorer()
        with explorer.update() as updater:

            if db_type == "dballe" or db_type == "mixed":
                if need_filtered:
                    summary_file_prefix = BeDballe.DBALLE_JSON_SUMMARY_PATH_FILTERED
                else:
                    summary_file_prefix = BeDballe.DBALLE_JSON_SUMMARY_PATH

                summary_file_suffix = license_group.name.replace(" ", "_")
                json_summary_file = Path(
                    f"{summary_file_prefix}_{summary_file_suffix}.json"
                )
                # log.debug("dballe summary file{}", json_summary_file)
                log.debug("loaded in explorer {}", json_summary_file)
                if json_summary_file.exists():
                    with open(json_summary_file) as fd:
                        updater.add_json(fd.read())

            if db_type == "arkimet" or db_type == "mixed":
                if need_filtered:
                    summary_file_prefix = BeDballe.ARKI_JSON_SUMMARY_PATH_FILTERED
                else:
                    summary_file_prefix = BeDballe.ARKI_JSON_SUMMARY_PATH

                summary_file_suffix = license_group.name.replace(" ", "_")
                json_summary_file = Path(
                    f"{summary_file_prefix}_{summary_file_suffix}.json"
                )

                log.debug("loaded in explorer {}", json_summary_file)
                if json_summary_file.exists():
                    with open(json_summary_file) as fd:
                        updater.add_json(fd.read())
        return explorer

    @staticmethod
    def get_summary(params, explorer, query=None, fields=None, queries=None):
        """
        SUMMARY MESSAGES AND SIZE COUNT BRIEF EXPLANATION.
        If no timerange, or level, or product were chosen in the query, messages and size count works differently,
        and we have to define a reference cursor for every station and every query
        (it shall be the one with maximum message count).
        In this case, it is necessary to adopt a different ("non-standard") method for size counting:
        "BeDballe.get_non_standard_size_and_message_count()".
        This is necessary to avoid counting messages twice during the iteration on query cursors:
        DBAllE employs an internal mechanism to aggregate data from variables with identical demographic attributes.
        Only reference cursors add their number of messages and their anagraphical attributes bits to the total count.
        Non-reference cursors only contribute bits for the physical variables and for any newly-covered attributes.
        If at least one filter is chosen for timerange, level, and product there's no need for a "non-standard" method
        for size counting (further details in "__get_query_important_params" method's documentation).
        In the case where the "multimodel-forecast" dataset has been selected, size count is not available and the old
        message count method will be used. In the future, reliable size and message count methods may be implemented
        for the "multimodel-forecast" case as well.
        ITA:
        Se non è stato definito nessun timerange, o livello o prodotto nella query, la messages e size count
        funziona in maniera diversa e dobbiamo stabilire un cursore di riferimento per ogni stazione e per ogni query
        (sarà quello con la message count massima).
        In questo caso, bisogna adottare il metodo "non-standard" per calcolare la size count
        "BeDballe.get_non_standard_size_and_message_count()".
        Questo è necessario al fine di non contare doppiamente i messaggi quando scorriamo tra i cursori della query:
        DBAllE ha un meccanismo interno di aggregazione dei dati di variabili con uguali attributi anagrafici.
        Solo i cursori di riferimento aggiungono il loro numero di messaggi e i bit dei loro attributi anagrafici al
        conteggio totale, mentre i cursori non di riferimento contribuiscono solo con i bit per le variabili fisiche e
        per eventuali nuovi attributi coperti.
        Se almeno un filtro è selezionato per ogni tipo, non c'è bisogno di un metodo "non-standard" per il
        conteggio delle dimensioni (maggiori dettagli nella documentazione del metodo "__get_query_important_params").
        Nel caso in cui sia stato selezionato il dataset "multimodel-forecast", il conteggio della size
        non sarà possibile e verrà utilizzato il vecchio metodo di conteggio dei messaggi. In futuro si potrebbero
        implementare metodi di size e message count affidabili anche per il caso "multimodel-forecast".
        """

        # When get_summary is called by data API, fields and queries are already given
        if not fields or not queries:
            if params and "network" not in query:
                query["network"] = params
            fields, queries = BeDballe.from_query_to_lists(query)

        log.debug("Counting messages: fields: {}, queries: {}", fields, queries)

        # get all the possible combinations of queries to count the messages
        all_queries = list(itertools.product(*queries))

        # "query_important_params" contains info and flags that lead us to the correct way of counting messages and
        # size, as explained in the comments of the method
        query_important_params = BeDballe.__get_query_important_params(
            params, fields, queries
        )
        # Obtaining the Vartables containing all BUFR variable codes.
        # This is necessary to retrieve physical variables' encoding bits.
        vartables = BeDballe.get_wreport_vartables()

        # Dictionary to be populated with bits accounting for physical variables (as total bits needed for encoding
        # and descriptor in BUFR messages)
        physical_variable_bits_dict: {str: int} = {}

        # messages and size counters
        message_count = 0
        size_count = 0

        # date boundaries for Summary
        summary_min_date: Optional[datetime] = None
        summary_max_date: Optional[datetime] = None

        for q in all_queries:
            dballe_query = {k: v for k, v in zip(fields, q)}
            dballe_query["query"] = "details"

            explorer.set_filter(dballe_query)
            log.debug("counting query: {}", dballe_query)

            all_stations_reference_data = {}
            cursor_effective_datetime_dict = {}

            if any(
                not query_field
                for query_field in [
                    explorer.varcodes,
                    explorer.tranges,
                    explorer.levels,
                ]
            ):
                # If any query_field is empty, query returns no data so no further logic is needed for this cursor
                continue

            if query_important_params["is_multim_forecast"]:
                # Size count is currently not available for multimodel case, we can only count the number of messages
                for cur in explorer.query_summary(dballe_query):
                    (
                        message_count,
                        summary_min_date,
                        summary_max_date,
                    ) = BeDballe.__get_message_count_for_multimodel_forecast(
                        cur, message_count, summary_min_date, summary_max_date
                    )
                continue

            if query_important_params["need_different_size_count"]:
                # We need to populate 'all_stations_reference_data' in order to compute the non-standard size and
                # message count
                for cur in explorer.query_summary(dballe_query):
                    cur_original_dt_interval = (cur["datetimemin"], cur["datetimemax"])

                    effective_messages = BeDballe.__get_effective_messages_number(
                        cur["count"],
                        cur_original_dt_interval,
                        query_important_params["query_original_dt_interval"],
                        cursor_effective_datetime_dict,
                    )

                    if effective_messages > 0:

                        BeDballe.__populate_all_stations_reference_data(
                            cur,
                            effective_messages,
                            query_important_params["selected_filters_keys"],
                            all_stations_reference_data,
                        )

            for cur in explorer.query_summary(dballe_query):
                cur_original_dt_interval = (cur["datetimemin"], cur["datetimemax"])

                effective_messages = BeDballe.__get_effective_messages_number(
                    cur["count"],
                    cur_original_dt_interval,
                    query_important_params["query_original_dt_interval"],
                    cursor_effective_datetime_dict,
                )

                # Message and size counts, as well as summary time interval boundaries, are updated only when the cursor
                # effectively contributes messages.
                if effective_messages > 0:
                    cur_effective_dt_interval = cursor_effective_datetime_dict[
                        cur_original_dt_interval
                    ]["cur_effective_dt_interval"]

                    message_count, size_count, = BeDballe.__get_messages_and_size_count(
                        cur,
                        effective_messages,
                        physical_variable_bits_dict,
                        query_important_params,
                        all_stations_reference_data,
                        vartables,
                        size_count,
                        message_count,
                    )

                    (
                        summary_min_date,
                        summary_max_date,
                    ) = BeDballe.__adjust_summary_time_interval_boundaries(
                        cur_effective_dt_interval, summary_min_date, summary_max_date
                    )

        # create the summary
        summary: Dict[str, Union[int, List[str], List[int], type(None)]] = {}

        log.debug("message_count: " + str(message_count))
        log.debug("bits_size_count: " + str(math.floor(size_count / 8)))

        if not message_count:
            return summary
        else:
            summary["c"] = message_count
            if not query_important_params["is_multim_forecast"]:
                summary["s"] = math.floor(size_count / 8)
            else:
                # Multimodel forecast size count is not available, so size count shall be None
                summary["s"] = None

            # Probably, if the multim-forecast case had been managed, the next block could be substituted by
            # the following line of code:
            # summary["b"] = BeDballe.from_datetime_to_list(summary_min_date)
            if fields and "datetimemin" in fields:
                q_dtmin_index = fields.index("datetimemin")
                q_dtmin = queries[q_dtmin_index][0]
                if summary_min_date and summary_min_date > q_dtmin:
                    summary["b"] = BeDballe.from_datetime_to_list(summary_min_date)
                else:
                    summary["b"] = BeDballe.from_datetime_to_list(q_dtmin)
            else:
                summary["b"] = BeDballe.from_datetime_to_list(summary_min_date)

            # Probably, if the multim-forecast case had been managed, the next block could be substituted by
            # the following line of code:
            # summary["e"] = BeDballe.from_datetime_to_list(summary_max_date)
            if fields and "datetimemax" in fields:
                q_dtmax_index = fields.index("datetimemax")
                q_dtmax = queries[q_dtmax_index][0]
                if summary_max_date and summary_max_date < q_dtmax:
                    summary["e"] = BeDballe.from_datetime_to_list(summary_max_date)
                else:
                    summary["e"] = BeDballe.from_datetime_to_list(q_dtmax)
            else:
                summary["e"] = BeDballe.from_datetime_to_list(summary_max_date)

            return summary

    @staticmethod
    def __get_message_count_for_multimodel_forecast(
        cursor, message_count, summary_min_date, summary_max_date
    ):
        """
        This is the old method of counting the number of messages for multimodel-forecast.
        Size count is not currently available for multimodel-forecast.
        """

        message_count += cursor["count"]

        datetimemin = cursor["datetimemin"]
        datetimemax = cursor["datetimemax"]

        if summary_min_date:
            if datetimemin < summary_min_date:
                summary_min_date = datetimemin
        else:
            summary_min_date = datetimemin
        if summary_max_date:
            if datetimemax > summary_max_date:
                summary_max_date = datetimemax
        else:
            summary_max_date = datetimemax

        return message_count, summary_min_date, summary_max_date

    @staticmethod
    def __get_query_important_params(params, fields, queries):
        """
        ENG:
        The boolean 'need_different_size_count' precisely distinguishes the case where it is necessary to adopt
        a different ("non-standard") method for size counting: "BeDballe.get_non_standard_size_and_message_count()".
        If filters for time range, level, or product type are selected, 'selected_filters_keys' will capture the
        chosen filter types.
        This is necessary because we will require reference cursors for every possible combination of the
        selected filter variable values.
        If at least one filter is chosen for each type, 'selected_filters_keys' will be empty.
        In this scenario, there's no need for a "non-standard" method for size counting,
        and 'need_different_size_count' will be set to false.
        ITA:
        Il booleano "need_different_size_count" distingue appunto il caso in cui bisogna adottare il
        metodo "non-standard" per calcolare la size count: "BeDballe.get_non_standard_size_and_message_count()".
        Se sono selezionati filtri per l'intervallo di tempo, il livello o il tipo di prodotto,
        'selected_filters_keys' catturerà i tipi di filtri scelti.
        Questo è necessario perché avremo bisogno di cursori di riferimento per ogni possibile combinazione dei
        valori delle variabili dei filtri selezionati.
        Se almeno un filtro è selezionato per ogni tipo, allora 'selected_filters_keys' sarà vuoto.
        In questo scenario, non c'è bisogno di un metodo "non-standard" per il conteggio delle dimensioni,
        e 'need_different_size_count' sarà impostato su false.
        """
        query_important_params = {
            "query_original_dt_interval": {},
            "selected_filters_keys": [],
            "need_different_size_count": any(
                query_field not in fields for query_field in ["trange", "level", "var"]
            ),
            "is_multim_forecast": "multim-forecast" in params,
        }

        # datetime interval of the query
        if fields:
            if "datetimemin" in fields:
                query_important_params["query_original_dt_interval"][
                    "datetimemin"
                ] = queries[fields.index("datetimemin")][0]
            if "datetimemax" in fields:
                query_important_params["query_original_dt_interval"][
                    "datetimemax"
                ] = queries[fields.index("datetimemax")][0]

        if query_important_params["need_different_size_count"]:
            query_important_params["selected_filters_keys"] = [
                query_key
                for query_key in ["trange", "level", "var"]
                if (query_key in fields and queries[fields.index(query_key)][0])
            ]

        return query_important_params

    @staticmethod
    def get_wreport_vartables():

        principal_vartable = None
        secondary_vartable = None
        master_table_version_number = 31
        try:
            principal_vartable = wreport.Vartable.get_bufr(
                master_table_version_number=master_table_version_number
            )
        except Exception as e:
            log.warning(
                f"It was not possible to obtain principal Vartable with "
                f"master_table_version_number={master_table_version_number}, {e}"
            )
        # the secondary Vartable serves as an additional method in case the first one fails to include all possible
        # B variables
        try:
            secondary_vartable = wreport.Vartable.get_bufr(basename="dballe")
        except Exception as e:
            log.warning(
                f"It was not possible to obtain secondary Vartable with basename=dballe, {e}"
            )

        if not isinstance(principal_vartable, wreport.Vartable) and not isinstance(
            secondary_vartable, wreport.Vartable
        ):
            log.warning(
                "Physical variables' encoding bits will not be considered for size count as it was not possible "
                "to retrieve Vartables from wreport folder: 'usr/share/wreport'"
            )

        vartables = {
            "principal_vartable": principal_vartable,
            "secondary_vartable": secondary_vartable,
        }

        return vartables

    @staticmethod
    def __populate_all_stations_reference_data(
        cur, effective_messages, selected_filters_keys, all_stations_reference_data
    ):
        """
        The purpose of this function is to find, for each station, which cursor to consider as a reference for every
        combination of parameters selected as filters in the query (time_range, level, product).
        For each station and for every combination of filter parameters, the reference cursor will be the one
        with the highest number of messages.
        Non-reference cursors' do not increase the number of messages and need a different size count because their
        (new) data is aggregated into messages of the reference cursors, sharing same demographic attributes.
        """

        filters_values = (
            "no_filters_selected"
            if not selected_filters_keys
            else tuple(cur[key] for key in selected_filters_keys)
        )

        # Update all_stations_reference_data if station ID is already in the dictionary
        if cur["ana_id"] not in all_stations_reference_data:
            all_stations_reference_data[cur["ana_id"]] = {}

        if (
            filters_values not in all_stations_reference_data[cur["ana_id"]]
            or effective_messages
            > all_stations_reference_data[cur["ana_id"]][filters_values][
                "ref_eff_mex_count"
            ]
        ):
            all_stations_reference_data[cur["ana_id"]][filters_values] = {
                "ref_trange": cur["trange"],
                "ref_var": cur["var"],
                "ref_level": cur["level"],
                "ref_eff_mex_count": effective_messages,
                # 'datetimes_covered': [list(cur_effective_dt_interval)],
                "tranges_covered": [cur["trange"]],
                "levels_covered": [cur["level"]],
            }
        else:
            pass

    @staticmethod
    def __get_effective_messages_number(
        cursor_messages,
        cur_original_dt_interval,
        query_original_dt_interval,
        cursor_effective_datetime_dict,
    ):
        """
        If cursor's datetime interval is not the same as query's one (if present), we have to consider just a fraction
        of cursor's messages count.

        The 'cursor_effective_datetime_dict' dictionary is populated with important cursor data gathered during the
        run. This dictionary consists of original cursor datetime intervals as keys and another dictionary as values.
        For each entry in the 'cursor_effective_datetime_dict' dictionary, we can access the values of the keys,
        'cur_vs_query_dtime_ratio' and 'cur_effective_dt_interval', which respectively indicate how much the cursor
        'effectively' contributes messages to the final count and the 'effective'
        portion of the cursor's datetime interval.
        """

        if cur_original_dt_interval not in cursor_effective_datetime_dict:

            cursor_effective_datetime_dict[
                cur_original_dt_interval
            ] = BeDballe.__populate_cursor_effective_datetime_dict(
                cur_original_dt_interval, query_original_dt_interval
            )

        cur_vs_query_dtime_ratio = cursor_effective_datetime_dict[
            cur_original_dt_interval
        ]["cur_vs_query_dtime_ratio"]

        # cur_vs_query_dtime_ratio = -1 -> refers to the case "query_dtime_interval"
        # is not an actual interval but just a point on the timeline.
        # Thus, we shall consider this cursor's message count equal to 1
        effective_messages = (
            math.floor(cursor_messages * cur_vs_query_dtime_ratio)
            if cur_vs_query_dtime_ratio >= 0
            else 1
        )

        return effective_messages

    @staticmethod
    def __populate_cursor_effective_datetime_dict(cur_original_dt, query_original_dt):
        """
        This function compares cursor's datetime interval to query's one.
        This is needed to obtain a coefficient which is used to get the number of effective messages
        the cursor brings to the final count.
        While doing so, we trim cursor's original datetime interval to make it fit within the query datetime
        interval.
        """

        if not cur_original_dt:
            return {"cur_vs_query_dtime_ratio": 0, "cur_effective_dt_interval": []}
        else:
            original_cur_dt_int_duration = (
                cur_original_dt[1] - cur_original_dt[0]
            ).total_seconds()

        if not query_original_dt:

            return {
                "cur_vs_query_dtime_ratio": 1
                if original_cur_dt_int_duration != 0
                else -1,
                "cur_effective_dt_interval": list(cur_original_dt),
            }
        else:
            if all(
                date_key in query_original_dt
                for date_key in ("datetimemin", "datetimemax")
            ):
                query_dt = [
                    query_original_dt["datetimemin"],
                    query_original_dt["datetimemax"],
                ]
            elif "datetimemin" not in query_original_dt:
                if cur_original_dt[0] <= query_original_dt["datetimemax"]:
                    query_dt = [cur_original_dt[0], query_original_dt["datetimemax"]]
                else:
                    query_dt = [
                        query_original_dt["datetimemax"],
                        query_original_dt["datetimemax"],
                    ]
            # if 'datetimemax' is missing and only 'datetimemin' is in query_original_dt
            else:
                if cur_original_dt[1] >= query_original_dt["datetimemin"]:
                    query_dt = [query_original_dt["datetimemin"], cur_original_dt[1]]
                else:
                    query_dt = [
                        query_original_dt["datetimemin"],
                        query_original_dt["datetimemin"],
                    ]

        # Check if cursor time interval is external to query time interval
        if query_dt[1] < cur_original_dt[0] or cur_original_dt[1] < query_dt[0]:
            return {
                "cur_vs_query_dtime_ratio": 0,
                "cur_effective_dt_interval": list(cur_original_dt),
            }

        # Check if the cursor time interval is within query time interval
        elif query_dt[0] <= cur_original_dt[0] <= cur_original_dt[1] <= query_dt[1]:
            return {
                "cur_vs_query_dtime_ratio": -1
                if original_cur_dt_int_duration == 0
                else 1,
                "cur_effective_dt_interval": list(cur_original_dt),
            }

        # Check if the query time interval is entirely within the cursor time interval
        elif cur_original_dt[0] <= query_dt[0] <= query_dt[1] <= cur_original_dt[1]:
            cur_effective_dt_interval = [dtime for dtime in query_dt]
        else:
            # this is the case cur_original_dt overlaps the query_dt,
            # the cursor effective time interval is given by just the overlapping region
            if query_dt[0] <= cur_original_dt[0] <= query_dt[1]:
                # cur_original_dt overlaps from right
                cur_effective_dt_interval = [cur_original_dt[0], query_dt[1]]
            else:  # condition: query_dt[0] <= cur_original_dt[1] <= query_dt[1]
                # cur_original_dt overlaps from left
                cur_effective_dt_interval = [query_dt[0], cur_original_dt[1]]

        # We compute the ratio between the effective time interval of this cursor and the total datetime of the
        # original cursor
        effective_cur_dt_int_duration = (
            cur_effective_dt_interval[1] - cur_effective_dt_interval[0]
        ).total_seconds()

        cur_vs_query_dtime_ratio = (
            -1
            if effective_cur_dt_int_duration == 0
            else effective_cur_dt_int_duration / original_cur_dt_int_duration
        )

        return {
            "cur_vs_query_dtime_ratio": cur_vs_query_dtime_ratio,
            "cur_effective_dt_interval": cur_effective_dt_interval,
        }

    @staticmethod
    def __get_messages_and_size_count(
        cur,
        effective_messages,
        physical_variable_bits_dict,
        query_important_params,
        all_stations_reference_data,
        vartables,
        size_count,
        message_count,
    ):

        is_this_cursor_the_reference = False
        new_attr_covered_flags = None

        need_different_size_count = query_important_params["need_different_size_count"]

        if need_different_size_count:
            # We check if the current cursor is the reference one. If it isn't, we obtain flags to keep track for bits
            # compensation when a new attribute is covered by a non-reference cursor.
            (
                is_this_cursor_the_reference,
                new_attr_covered_flags,
            ) = BeDballe.__check_is_this_cursor_reference_or_new_attributes_are_covered(
                cur,
                query_important_params["selected_filters_keys"],
                all_stations_reference_data,
            )

        if not need_different_size_count or is_this_cursor_the_reference:
            # This is the standard way of counting the size for the average type of message.
            size_count, message_count = BeDballe.__get_standard_size_and_message_count(
                cur,
                effective_messages,
                physical_variable_bits_dict,
                vartables,
                size_count,
                message_count,
            )
        else:
            # The following is the way of counting messages and size in case the query had no timerange
            # or level or product parameter (and current cursor is not the reference one for the station).
            (
                size_count,
                message_count,
            ) = BeDballe.get_non_standard_size_and_message_count(
                cur,
                effective_messages,
                physical_variable_bits_dict,
                new_attr_covered_flags,
                vartables,
                size_count,
                message_count,
            )

        return message_count, size_count

    @staticmethod
    def __check_is_this_cursor_reference_or_new_attributes_are_covered(
        cur, selected_filters_keys, all_stations_reference_data
    ):

        new_attr_flags = {}

        filter_values = (
            "no_filters_selected"
            if not (selected_filters_keys)
            else tuple([cur[key] for key in selected_filters_keys])
        )

        station_summary_data = all_stations_reference_data[cur["ana_id"]][
            filter_values
        ]  # cur['ana_id'] is station ID

        is_this_cursor_the_reference = all(
            cur[cur_field_key] == station_summary_data[reference_field_key]
            for cur_field_key, reference_field_key in BeDballe.IS_REF_CUR_CHECKS
        )

        if not is_this_cursor_the_reference:
            # We now obtain flags to keep track for bits compensation when a new attribute is covered by
            # a non-reference cursor.
            for cur_key, covered_fields, field_attr in BeDballe.NEW_ATTR_COVERED_CHECKS:
                if cur[cur_key] is None:
                    new_attr_flags[cur_key] = False
                else:
                    new_attr_flags[cur_key] = BeDballe.__check_new_attr_covered(
                        station_summary_data[covered_fields], field_attr, cur[cur_key]
                    )

            # Updating covered attributes lists for the station_summary_data (i.e. for the current station_id and
            # the set of filter_values at hand)
            for cursor_field, covered_fields in [
                (cur["trange"], "tranges_covered"),
                (cur["level"], "levels_covered"),
            ]:
                if cursor_field not in station_summary_data[covered_fields]:
                    station_summary_data[covered_fields].append(cursor_field)

        return is_this_cursor_the_reference, new_attr_flags

    @staticmethod
    def __check_new_attr_covered(covered_fields, field_attr, cursor_attribute):
        for field in covered_fields:
            if getattr(field, field_attr) == cursor_attribute:
                return False
        else:
            return True

    @staticmethod
    def __get_standard_size_and_message_count(
        cursor,
        effective_messages,
        physical_variable_bits_dict,
        vartables,
        size_count,
        message_count,
    ):

        # If additional level attributes are present, we add bits accounting for encoding and descriptor
        # of those as the sum of: bits_section_3 += 16, bits_attr_encoding += 31
        add_level_bits = 0
        for cur_key in BeDballe.LEVEL_ATTR_CUR_KEYS:
            add_level_bits += 47 if cursor[cur_key] else 0

        # Total number of bits for the physical variable
        phys_var_total_bits = BeDballe.__get_physical_variable_bits(
            vartables, physical_variable_bits_dict, cursor["var"]
        )

        total_bits_per_message = (
            BeDballe.STANDARD_FIXED_BITS
            + BeDballe.STANDARD_SECTION_3_BITS
            + BeDballe.STANDARD_ATTR_ENCODING_BITS
            + add_level_bits
            + phys_var_total_bits
        )

        size_count += total_bits_per_message * effective_messages

        message_count += effective_messages

        return size_count, message_count

    @staticmethod
    def __get_physical_variable_bits(vartables, physical_variable_bits_dict, var_code):
        """
        This method calculates the number of bits needed to encode the value of the physical variable. It then adds 16
        to this number, representing the bits required for the variable in SECTION 3 of the BUFR message.
        Consequently, the method returns the total bit count for the physical variable.
        """
        phys_var_encoding_bits = 0
        principal_vartable = vartables["principal_vartable"]
        secondary_vartable = vartables["secondary_vartable"]

        if not isinstance(principal_vartable, wreport.Vartable) and not isinstance(
            secondary_vartable, wreport.Vartable
        ):
            # It was not possible to retrieve Vartables from wreport folder 'usr/share/wreport'
            phys_var_total_bits = 16  # 16 + phys_var_encoding_bits = 16 + 0 = 16
            return phys_var_total_bits

        if var_code not in physical_variable_bits_dict:
            b_table_variable = None

            if isinstance(principal_vartable, wreport.Vartable):
                try:
                    b_table_variable = principal_vartable[var_code]
                except KeyError:
                    pass
                    # log.warning(
                    #     f"B code {var_code} variable's bit size cannot be obtained from principal Vartable. "
                    #     f"KeyError Exception message: {e}"
                    # )

            if not b_table_variable and isinstance(
                secondary_vartable, wreport.Vartable
            ):
                try:
                    b_table_variable = secondary_vartable[var_code]
                    # log.info(
                    #     f"Variable {var_code} bit size was obtained from secondary Vartable: {secondary_vartable}"
                    # )
                except KeyError as e:
                    log.warning(
                        f"B code {var_code} variable's bit size cannot be obtained from either the primary or the "
                        f"secondary Vartable. "
                        f"KeyError Exception message: {e}"
                    )

            if b_table_variable:
                # Retrieving the physical variable
                phys_variable = wreport.Var(b_table_variable)
                # Bits that account for the physical variable encoding
                phys_var_encoding_bits = phys_variable.info.bit_len

            # Total number of bits for the physical variable as sum of encoding-bits and 16 bits for SECTION 3
            physical_variable_bits_dict[var_code] = 16 + phys_var_encoding_bits

        phys_var_total_bits = physical_variable_bits_dict[var_code]

        return phys_var_total_bits

    @staticmethod
    def get_non_standard_size_and_message_count(
        cur,
        effective_messages,
        physical_variable_bits_dict,
        new_attr_covered_flags,
        vartables,
        size_count,
        message_count,
    ):
        # If any of the new_attr_covered_flags is true, the current cursor extends to include
        # attributes not covered by the reference cursor. We add bits for encoding and descriptors accordingly.
        # The number of bits is determined by the 'NEW_ATTR_BITS' dictionary.
        add_new_attr_bits = 0
        for cur_key in BeDballe.LEVEL_AND_TRANGES_CUR_KEYS:
            add_new_attr_bits += (
                BeDballe.NEW_ATTR_BITS[cur_key]
                if new_attr_covered_flags[cur_key]
                else 0
            )

        # Total number of bits for the physical variable
        phys_var_total_bits = BeDballe.__get_physical_variable_bits(
            vartables, physical_variable_bits_dict, cur["var"]
        )

        size_count += (add_new_attr_bits + phys_var_total_bits) * effective_messages

        return size_count, message_count

    @staticmethod
    def __adjust_summary_time_interval_boundaries(
        cur_effective_dt_interval, min_date, max_date
    ):

        if not min_date or cur_effective_dt_interval[0] < min_date:
            # extend the left boundary min_date with datetimemin of the cursor row
            min_date = cur_effective_dt_interval[0]

        if not max_date or cur_effective_dt_interval[1] > max_date:
            # extend the right boundary max_date with datetimemax of the cursor row
            max_date = cur_effective_dt_interval[1]

        return min_date, max_date

    @staticmethod
    def load_filters(
        params,
        summary_stats,
        all_products,
        db_type,
        license_group,
        query_dic=None,
        queried_reftime=None,
    ):
        query = {}
        if query_dic:
            query = {**query_dic}

        log.info("Loading filters dataset: {}, query: {}", params, query)

        # check if requested networks are in that dataset
        query_networks_list = []
        if params:
            if "network" in query:
                if not all(elem in params for elem in query["network"]):
                    return None, None
                else:
                    query_networks_list = query["network"]
            else:
                # in case of no requested network data will be only filtered by dataset
                query_networks_list = params

        log.debug(f"Loading filters: query networks list : {query_networks_list}")

        bbox = {}
        bbox_keys = ["latmin", "lonmin", "latmax", "lonmax"]
        for key, value in query.items():
            if key in bbox_keys:
                bbox[key] = value

        # create and update the explorer object
        explorer = BeDballe.build_explorer(db_type, license_group, query_networks_list)

        # perform the queries in database to get the list of possible filters
        fields = {}
        network_products = []
        networks_list = []
        variables = []
        levels = []
        tranges = []
        filters_for_explorer = {}
        if bbox:
            for key, value in bbox.items():
                filters_for_explorer[key] = value
        if "datetimemin" in query:
            filters_for_explorer["datetimemin"] = query["datetimemin"]
            filters_for_explorer["datetimemax"] = query["datetimemax"]

        if not query_networks_list:
            # if there isn't a query network list, it's observed maps case
            # (the data extraction is always managed using datasets)
            explorer.set_filter(filters_for_explorer)
            # list of the variables of the query without level and timerange costraints
            # (used in "all available products" case)
            network_products = explorer.varcodes
            # add all values of the query to the filter for explorer
            # (N.B. i can do that only because i am in the maps case
            # and i am sure that queries are all single param)
            if query:
                parsed_query = BeDballe.parse_query_for_maps(query)
                for key, value in parsed_query.items():
                    filters_for_explorer[key] = value
            explorer.set_filter(filters_for_explorer)

            # ####### VARIABLES FIELDS
            # get the list of the variables coming from the query
            variables = explorer.varcodes

            # ######## LEVELS FIELDS
            level_fields = explorer.levels
            if level_fields:
                for el in level_fields:
                    levels.append(BeDballe.from_level_object_to_string(el))
            # ######## TIMERANGES FIELDS
            trange_fields = explorer.tranges
            if trange_fields:
                for el in trange_fields:
                    tranges.append(BeDballe.from_trange_object_to_string(el))
            # ######## NETWORKS FIELDS
            networks_list = explorer.reports

        else:
            # get the fields network by network for the requested networks
            n_total_runs = 0
            for n in query_networks_list:

                # filter the dballe database by network
                filters_for_explorer["report"] = n

                explorer.set_filter(filters_for_explorer)

                # list of the variables of this network
                net_variables = []

                # ######## VARIABLES FIELDS
                # get the list of all the variables of the network
                varlist = explorer.varcodes
                # append all the products available for that network
                # (not filtered by the query)
                if varlist:
                    network_products.extend(
                        x for x in varlist if x not in network_products
                    )

                # #### PRODUCT is in the query filters
                if "product" in query:
                    # check if the requested variables are in the network
                    for e in query["product"]:
                        # if there is append to the temporary list of matching variables
                        if e in varlist:
                            net_variables.append(e)
                    if not net_variables:
                        # if at the end of the cycle the temporary list of matching
                        # variables is still empty go to the next network
                        continue
                else:
                    # if product is not in the query filter append all the variable
                    # of the network o the final list of the fields
                    net_variables = varlist

                # ######## LEVELS FIELDS
                level_fields, net_variables_temp = BeDballe.get_fields(
                    explorer, filters_for_explorer, net_variables, query, param="level"
                )
                if not level_fields:
                    continue
                # check if the temporary list of variable is not more little of
                # the general one. If it is, replace the general list
                if not all(elem in net_variables_temp for elem in net_variables):
                    net_variables = net_variables_temp

                # ######## TIMERANGES FIELDS
                if n != "multim-forecast" or not queried_reftime:
                    (
                        trange_fields,
                        net_variables_temp,
                        level_fields_temp,
                    ) = BeDballe.get_fields(
                        explorer,
                        filters_for_explorer,
                        net_variables,
                        query,
                        param="timerange",
                    )
                else:
                    total_runs = query["datetimemax"] - query["datetimemin"]
                    n_total_runs = total_runs.days
                    # if not n_total_runs:
                    #     # only one run is requested
                    #     n_total_runs = 1
                    trange_fields = []
                    net_variables_temp = []
                    level_fields_temp = []
                    for i in range(n_total_runs + 1):
                        reftime_to_check = query["datetimemin"] + timedelta(days=i)
                        log.debug("reftime to check: {}", reftime_to_check)
                        if not query["datetimemin"] == reftime_to_check:
                            reftime_to_check = reftime_to_check.replace(
                                hour=0, minute=0
                            )
                        (
                            part_trange_fields,
                            part_net_variables_temp,
                            part_level_fields_temp,
                        ) = BeDballe.get_fields(
                            explorer,
                            filters_for_explorer,
                            net_variables,
                            query,
                            param="timerange",
                            run_to_check=reftime_to_check,
                        )
                        if part_trange_fields:
                            trange_fields.extend(
                                x for x in part_trange_fields if x not in trange_fields
                            )
                            net_variables_temp.extend(
                                x
                                for x in part_net_variables_temp
                                if x not in net_variables_temp
                            )
                            level_fields_temp.extend(
                                x
                                for x in part_level_fields_temp
                                if x not in level_fields_temp
                            )
                if not trange_fields:
                    continue
                # check if the temporary list of variable is not more little of
                # the general one. If it is, replace the general list
                if not all(elem in net_variables_temp for elem in net_variables):
                    net_variables = net_variables_temp

                # check if the temporary list of levels is not more little
                # f the general one. If it is, replace the general list
                if not all(elem in level_fields_temp for elem in level_fields):
                    level_fields = level_fields_temp

                # append in the final list the timeranges retrieved
                tranges.extend(x for x in trange_fields if x not in tranges)

                # append in the final list the levels retrieved
                levels.extend(x for x in level_fields if x not in levels)

                # append all the network variables in the final field list
                variables.extend(x for x in net_variables if x not in variables)

                # if there are results, this network can be in the final fields
                networks_list.append(n)

        # if matching fields were found network list can't be empty
        if networks_list:
            # create the final dictionary
            fields["network"] = BeDballe.from_list_of_params_to_list_of_dic(
                networks_list, type="network"
            )
            fields["product"] = BeDballe.from_list_of_params_to_list_of_dic(
                variables, type="product"
            )
            fields["level"] = BeDballe.from_list_of_params_to_list_of_dic(
                levels, type="level"
            )
            fields["timerange"] = BeDballe.from_list_of_params_to_list_of_dic(
                tranges, type="timerange"
            )
            if all_products:
                fields[
                    "available_products"
                ] = BeDballe.from_list_of_params_to_list_of_dic(
                    network_products, type="product"
                )

            # create summary
            # if summary is required
            summary = {}
            if summary_stats:
                if not queried_reftime:
                    summary = BeDballe.get_summary(params, explorer, query=query)
                else:
                    # multimodel case
                    if len(params) > 1:
                        # not only multimodel is requested
                        params.remove("multim-forecast")
                        # restore the original requested datetimemax
                        query["datetimemax"] = queried_reftime
                        summary = BeDballe.get_summary(params, explorer, query=query)
                    for trange in fields["timerange"]:
                        params = ["multim-forecast"]
                        list = []
                        for v in trange["code"].split(","):
                            list.append(int(v))
                        timerange_interval = list[1]
                        for i in range(n_total_runs + 1):
                            reftime_to_check = query["datetimemin"] + timedelta(days=i)
                            log.debug("reftime to check: {}", reftime_to_check)
                            if not query["datetimemin"] == reftime_to_check:
                                reftime_to_check = reftime_to_check.replace(
                                    hour=0, minute=0
                                )
                            multim_summary_query = {}
                            multim_summary_query["datetimemin"] = multim_summary_query[
                                "datetimemax"
                            ] = reftime_to_check + timedelta(seconds=timerange_interval)
                            multim_summary_query["timerange"] = [trange["code"]]
                            # log.debug(
                            #     "query for multimodel summary: {}",
                            #     multim_summary_query
                            # )
                            part_summary = BeDballe.get_summary(
                                params, explorer, query=multim_summary_query
                            )
                            # log.debug("part summary: {}", part_summary)
                            if part_summary:
                                if not summary:
                                    summary = part_summary
                                    summary["b"] = BeDballe.from_datetime_to_list(
                                        reftime_to_check
                                    )
                                    summary["e"] = BeDballe.from_datetime_to_list(
                                        reftime_to_check
                                    )
                                else:
                                    summary["c"] += part_summary["c"]
                                    # case of query on multiple datasets:
                                    # check if the date min and the date max of the
                                    # summary of others dataset has to be considered
                                    if (
                                        part_summary["c"] != 0
                                        and datetime(*summary["e"]) < reftime_to_check
                                    ):
                                        summary["e"] = BeDballe.from_datetime_to_list(
                                            reftime_to_check
                                        )
                                    if (
                                        part_summary["c"] != 0
                                        and datetime(*summary["b"]) > reftime_to_check
                                    ):
                                        summary["b"] = BeDballe.from_datetime_to_list(
                                            reftime_to_check
                                        )
            return fields, summary
        else:
            return None, None

    @staticmethod
    def get_fields(
        explorer,
        filters_for_explorer,
        variables,
        query,
        param,
        run_to_check=None,
    ):
        # filter the dballe database by list of variables
        # (level and timerange depend on variable)
        filters_w_varlist = {**filters_for_explorer, "varlist": variables}
        explorer.set_filter(filters_w_varlist)

        level_list: List[Any] = []
        # get the list of all the fields for requested param according to the variables
        if param == "level":
            param_list = explorer.levels
        elif param == "timerange":
            param_list = explorer.tranges
            if run_to_check:
                # multimodel case: check for every timerange if actually exists
                # for the actual reftime and create list of levels accordingly
                # param_list_parsed, variables, level_list_parsed
                level_list = []
                query_for_tranges = {**filters_w_varlist}
                trange_to_remove = []
                for p in param_list:
                    query_for_tranges["datetimemin"] = query_for_tranges[
                        "datetimemax"
                    ] = run_to_check + timedelta(seconds=p.p1)
                    query_for_tranges["trange"] = p
                    # log.debug("query tranges: {}",query_for_tranges)
                    explorer.set_filter(query_for_tranges)
                    vars_by_trange = explorer.varcodes
                    if not vars_by_trange:
                        # append the timerange to the list of timeranges to remove
                        trange_to_remove.append(p)
                        continue
                    else:
                        level_list.extend(
                            x for x in explorer.levels if x not in level_list
                        )
                # log.debug("empty timeranges: {}", trange_to_remove)
                for tr in trange_to_remove:
                    param_list.remove(tr)
            else:
                # if the param is timerange, 3 values packed are needed
                level_list = explorer.levels

        # parse the dballe object
        param_list_parsed = []
        for e in param_list:
            if e is not None:
                if param == "level":
                    p = BeDballe.from_level_object_to_string(e)
                elif param == "timerange":
                    p = BeDballe.from_trange_object_to_string(e)
                param_list_parsed.append(p)
        level_list_parsed = []
        if level_list:
            # parse the level list
            for lev in level_list:
                if lev is not None:
                    level = BeDballe.from_level_object_to_string(lev)
                    level_list_parsed.append(level)

        # #### the param is in the query filters
        if param in query:
            temp_fields = []
            # check if the requested params matches the required for the given variables
            for e in query[param]:
                if e in param_list_parsed:
                    # if there is append it to the temporary list of matching fields
                    temp_fields.append(e)
            if not temp_fields:
                # if at the end of the cycle the temporary list of matching variables
                # is still empty go to the next network
                if param == "level":
                    return None, None
                elif param == "timerange":
                    return None, None, None
            else:
                # if only the param is in query and not product,
                # discard from the network list all products not matching the param
                if "product" not in query:
                    variables_by_param = []
                    levels_by_trange = []
                    for qp in query[param]:
                        # for each variable i check if the param matches
                        for v in variables:
                            filters_w_var = {**filters_for_explorer, "var": v}
                            # discard from the query the query params i don't need
                            filters_w_var.pop("report", None)
                            explorer.set_filter(filters_w_var)

                            if param == "level":
                                param_list = explorer.levels
                            elif param == "timerange":
                                param_list = explorer.tranges
                            # parse the dballe object
                            param_list_parsed = []
                            for e in param_list:
                                if param == "level":
                                    p = BeDballe.from_level_object_to_string(e)
                                elif param == "timerange":
                                    p = BeDballe.from_trange_object_to_string(e)
                                param_list_parsed.append(p)
                            # if the param matches append the variable in a temp list
                            if qp in param_list_parsed:
                                variables_by_param.append(v)
                    # the temporary list of variables matching the requested param
                    # become the list of the variable of the network
                    variables = variables_by_param
                    # if the list of variables has been modified, we are filtering
                    # by timeranges and level is not in query, i have to check if
                    # the level fields still matches the new variable list
                    if param == "timerange" and "level" not in query:
                        # for each variable check if the level matches
                        for level in level_list_parsed:
                            # discard from the query the query params i don't need
                            filters_w_varlist.pop("report", None)
                            explorer.set_filter(filters_w_varlist)

                            var_level = explorer.levels
                            var_level_parsed = []
                            # parse the dballe.Level object
                            for e in var_level:
                                lev = BeDballe.from_level_object_to_string(e)
                                var_level_parsed.append(lev)
                            # if the level matches append the level in a temporary list
                            if level in var_level_parsed:
                                levels_by_trange.append(level)
                        # the temporary list of levels matching the resulted variables
                        # become the list of levels to return
                        level_list_parsed = levels_by_trange
                if param == "level":
                    return temp_fields, variables
                elif param == "timerange":
                    return temp_fields, variables, level_list_parsed
        else:
            # if param is not in the query filter append return all the fields
            if param == "level":
                return param_list_parsed, variables
            elif param == "timerange":
                return param_list_parsed, variables, level_list_parsed

    @staticmethod
    def data_qc(attrs):
        attrs_dict = {v.code: v.get() for v in attrs}
        # Data already checked and checked as invalid by QC filter
        for key, val in attrs_dict.items():
            if key in BeDballe.QC_CODES and val < 50:
                # data is considered unreliable if its confidence is less than 50%
                return 0
        return 1

    @staticmethod
    def get_maps_response_for_mixed(
        query_data=None,
        only_stations=False,
        query_station_data=None,
        interval=None,
        dsn_subset=[],
        previous_res=None,
    ):
        # get data from the dballe database
        log.debug("mixed dbs: get data from dballe")
        query_for_dballe = {}
        if query_station_data:
            query_for_dballe = {**query_station_data}
        elif query_data:
            query_for_dballe = {**query_data}

        refmin_arki = None

        datetime_max = None
        datetime_min = None
        if "datetimemax" in query_for_dballe:
            datetime_max = query_for_dballe["datetimemax"]
        if "datetimemin" in query_for_dballe:
            datetime_min = query_for_dballe["datetimemin"]

        if datetime_min or datetime_max:
            (
                refmax_dballe,
                refmin_dballe,
                refmax_arki,
                refmin_arki,
            ) = BeDballe.split_reftimes(datetime_min, datetime_max)
            # set up query for dballe with the correct reftimes
            query_for_dballe["datetimemin"] = refmin_dballe
        else:
            # if there is no reftime i'll get the data of the last hour
            # TODO last hour or last day as default?
            # for production
            instant_now = datetime.now()
            # for local tests
            # today = date(2015, 12, 31)
            # time_now = datetime.now().time()
            # instant_now = datetime.combine(today, time_now)

            query_for_dballe["datetimemax"] = instant_now
            query_for_dballe["datetimemin"] = datetime.combine(
                instant_now, time(instant_now.hour, 0, 0)
            )

        if query_station_data:
            dballe_maps_data = BeDballe.get_maps_response(
                query_station_data=query_for_dballe,
                only_stations=only_stations,
                interval=interval,
                db_type="dballe",
                dsn_subset=dsn_subset,
                previous_res=previous_res,
            )
        else:
            dballe_maps_data = BeDballe.get_maps_response(
                query_data=query_for_dballe,
                only_stations=only_stations,
                interval=interval,
                db_type="dballe",
                dsn_subset=dsn_subset,
                previous_res=previous_res,
            )

        if query_for_dballe:
            # if there is not reftime, only the data of the last hour will be extracted
            if not datetime_min and not datetime_max:
                return dballe_maps_data
            else:
                # get data from the arkimet database
                log.debug("mixed dbs: get data from arkimet")
                query_for_arki = {}
                if query_station_data:
                    query_for_arki = {**query_station_data}
                elif query_data:
                    query_for_arki = {**query_data}

                # set up query for arkimet with the correct reftimes
                if refmin_arki:
                    query_for_arki["datetimemin"] = refmin_arki
                    query_for_arki["datetimemax"] = refmax_arki

                if query_station_data:
                    arki_maps_data = BeDballe.get_maps_response(
                        query_station_data=query_for_arki,
                        only_stations=only_stations,
                        interval=interval,
                        db_type="arkimet",
                        previous_res=dballe_maps_data,
                        dsn_subset=dsn_subset,
                    )
                else:
                    arki_maps_data = BeDballe.get_maps_response(
                        query_data=query_for_arki,
                        only_stations=only_stations,
                        interval=interval,
                        db_type="arkimet",
                        previous_res=dballe_maps_data,
                        dsn_subset=dsn_subset,
                    )

                if not dballe_maps_data and not arki_maps_data:
                    response: List[object] = []
                    return response

                if arki_maps_data:
                    return arki_maps_data

        return dballe_maps_data

    @staticmethod
    def get_maps_response(
        query_data=None,
        only_stations=False,
        interval=None,
        db_type=None,
        query_station_data=None,
        download=None,
        previous_res=None,
        dsn_subset=[],
        aggregations_dsn=None,
    ):
        # get the license group
        alchemy_db = sqlalchemy.get_instance()
        engine = alchemy_db.variables.get("dbtype")
        user = alchemy_db.variables.get("user")
        pw = alchemy_db.variables.get("password")
        host = alchemy_db.variables.get("host")
        port = alchemy_db.variables.get("port")
        if query_data:
            license_name = query_data["license"]
        else:
            license_name = query_station_data["license"]
        license_group = alchemy_db.GroupLicense.query.filter_by(
            name=license_name
        ).first()
        # get the dsn
        dballe_dsn = license_group.dballe_dsn
        if not dballe_dsn:
            log.error(
                "no dballe dsn configured for {} license group", query_data["license"]
            )
            raise WrongDbConfiguration

        if previous_res:
            # integrate the already existent response
            response = previous_res
        else:
            response = {}
        # choose the right query for the right situation
        # (station details response or default one)
        query = {}
        if query_station_data:
            parsed_query = BeDballe.parse_query_for_maps(query_station_data)
        elif query_data:
            parsed_query = BeDballe.parse_query_for_maps(query_data)

        query = {**parsed_query}

        # managing db_type
        if db_type == "arkimet":
            # manage bounding box for queries by station id
            bbox_for_arki = {}
            if query_data and "latmin" in query_data:
                bbox_for_arki["latmin"] = query_data["latmin"]
                bbox_for_arki["lonmin"] = query_data["lonmin"]
                bbox_for_arki["latmax"] = query_data["latmax"]
                bbox_for_arki["lonmax"] = query_data["lonmax"]
            # manage reftime for queries in arkimet
            datemin = None
            datemax = None
            if query_data:
                datemax = query["datetimemax"]
                if "datetimemin" in query:
                    datemin = query["datetimemin"]
            # for now we consider network as a single parameters.
            # TODO choose if the network will be a single or multiple param
            # transform network param in a list to be managed better for arkimet queries
            networks_as_list = None
            if query_data and "rep_memo" in query_data:
                networks_as_list = [query_data["rep_memo"]]
            query_for_arkimet = BeDballe.build_arkimet_query(
                datemin=datemin,
                datemax=datemax,
                network=networks_as_list,
                bounding_box=bbox_for_arki,
                dballe_query=query,
                license_group=license_group,
            )
            if query and not query_for_arkimet:
                # means that there aren't data in arkimet for this dballe query
                if download:
                    return None, {}, {}, None
                return []

            if networks_as_list:
                datasets = [
                    arki_service.from_network_to_dataset(query_data["rep_memo"])
                ]
            elif dsn_subset:
                datasets = dsn_subset
            else:
                # extract data from all the datasets of the selected dsn
                datasets = SqlApiDbManager.retrieve_dataset_by_dsn(
                    alchemy_db, dballe_dsn
                )

            if not datasets:
                if download:
                    return None, {}, {}, None
                return []

            log.debug("datasets: {}", datasets)
        mobile_db = None
        if db_type == "arkimet":
            db = BeDballe.fill_db_from_arkimet(datasets, query_for_arkimet)
        else:
            if aggregations_dsn:
                dballe_dsn = aggregations_dsn
            # connect to the correct dballe dsn
            try:
                db = dballe.DB.connect(
                    f"{engine}://{user}:{pw}@{host}:{port}/{dballe_dsn}"
                )
            except OSError:
                raise Exception(f"Unable to connect to dballe '{dballe_dsn}' database")
            # connect to the eventual dsn for mobile station
            mobile_db = None
            # to decomment when we will have mobile data
            # mobile_dsn = f"{dballe_dsn}_MOBILE"
            # try:
            #     mobile_db = dballe.DB.connect(
            #         f"{engine}://{user}:{pw}@{host}:{port}/{mobile_dsn}"
            #     )
            # except OSError:
            #     log.debug("{} dsn for mobile station data does not exists", dballe_dsn)
            #     mobile_db = None

        # if download param, return the db and the query to download the data
        if download:
            return db, query_data, query_station_data, mobile_db

        log.debug("start retrieving data: query data for maps {}", query)
        if db_type == "arkimet" or not dsn_subset:
            # extract all data in db
            response = BeDballe.extract_data_for_maps(
                db, query, query_station_data, response, only_stations
            )
            if mobile_db:
                # add the data extracted from the corresponding dsn for mobile stations
                response = BeDballe.extract_data_for_maps(
                    mobile_db, query, query_station_data, response, only_stations
                )
        else:
            log.debug("extraction from a dsn subset case")
            # get all networks of the requested datasets
            nets = []
            for ds in dsn_subset:
                for el in arki_service.get_observed_dataset_params(ds):
                    nets.append(el)
            for n in nets:
                # extract querying network by network
                query["rep_memo"] = n
                response = BeDballe.extract_data_for_maps(
                    db, query, query_station_data, response, only_stations
                )
                if mobile_db:
                    # add data extracted from the corresponding dsn for mobile stations
                    response = BeDballe.extract_data_for_maps(
                        mobile_db, query, query_station_data, response, only_stations
                    )

        return response

    @staticmethod
    def extract_data_for_maps(db, query, query_station_data, response, only_stations):
        with db.transaction() as tr:
            # check if query gives back a result
            count_data = tr.query_data(query).remaining
            # log.debug('count {}',count_data)
            if count_data == 0:
                return response
            # check if an extended response is requested:
            extend_res = False
            if query:
                if "level" not in query and "trange" not in query:
                    extend_res = True

            station_tuple: Tuple[Any, ...] = ()
            for rec in tr.query_data(query):
                # discard data from excluded networks
                if rec["rep_memo"] in BeDballe.MAPS_NETWORK_FILTER:
                    if "rep_memo" not in query:
                        continue
                    else:
                        if rec["rep_memo"] not in query["rep_memo"]:
                            continue
                query_for_details = {}
                if rec["ident"]:
                    station_tuple = (rec["ident"], rec["rep_memo"])
                    query_for_details["ident"] = rec["ident"]
                else:
                    station_tuple = (
                        float(rec["lat"]),
                        float(rec["lon"]),
                        rec["rep_memo"],
                    )
                    query_for_details["lat"] = float(rec["lat"])
                    query_for_details["lon"] = float(rec["lon"])
                query_for_details["rep_memo"] = rec["rep_memo"]

                if station_tuple not in response.keys():
                    response[station_tuple] = {}
                    details = []
                    if not query_station_data:
                        # append the variable of station name to the query for details
                        query_for_details["var"] = "B01019"
                    # add station details
                    for el in tr.query_station_data(query_for_details):
                        detail_el = {}
                        var = el["variable"]
                        code = var.code
                        detail_el["var"] = code
                        detail_el["val"] = var.get()
                        details.append(detail_el)

                    response[station_tuple]["details"] = details

                # get data values
                if not only_stations:
                    if (
                        not query_station_data
                        and not extend_res
                        and not rec["var"] in response[station_tuple].keys()
                    ):
                        response[station_tuple][rec["var"]] = []
                    product_val = {}
                    product_val["val"] = rec[rec["var"]].get()
                    reftime = datetime(
                        rec["year"],
                        rec["month"],
                        rec["day"],
                        rec["hour"],
                        rec["min"],
                        rec["sec"],
                    )
                    if "rep_memo" in query and query["rep_memo"] == "multim-forecast":
                        if "datetimemin" in query:
                            # multimodel case
                            # check if the data is from the requested run
                            actual_reftime = query["datetimemin"]
                            trange = rec["trange"]
                            validity_interval = timedelta(seconds=trange.p1)
                            if not actual_reftime == reftime - validity_interval:
                                # this data is not from the requested run
                                continue
                            else:
                                product_val["ref"] = reftime.isoformat()
                    else:
                        product_val["ref"] = reftime.isoformat()

                    if query:
                        if "query" in query:
                            # add reliable flag
                            variable = rec["variable"]
                            attrs = variable.get_attrs()
                            is_reliable = BeDballe.data_qc(attrs)
                            product_val["rel"] = is_reliable
                    if (
                        "rel" not in product_val.keys()
                        and rec["rep_memo"] != "multim-forecast"
                    ):
                        # QC filter is not active: use the default value (1)
                        # this param is not useful for multimodel use case
                        product_val["rel"] = 1

                    if query_station_data or extend_res:
                        level = BeDballe.from_level_object_to_string(rec["level"])
                        timerange = BeDballe.from_trange_object_to_string(rec["trange"])
                        product_tuple = (rec["var"], level, timerange)
                        if product_tuple not in response[station_tuple].keys():
                            response[station_tuple][product_tuple] = []
                        response[station_tuple][product_tuple].append(product_val)
                    else:
                        # append the value
                        response[station_tuple][rec["var"]].append(product_val)
        return response

    @staticmethod
    def parse_obs_maps_response(raw_res, only_last_data=False):
        log.debug("start parsing response for maps")
        response: Dict[str, Any] = {}
        response_data = []
        descriptions_dic = {}
        if raw_res:
            product_varcodes = []
            station_varcodes = []
            levels = []
            timeranges = []
            for key, value in raw_res.items():
                res_el: Dict[str, Any] = {}
                station_el = {}
                products_list = []
                if len(key) == 2:
                    station_el["ident"] = key[0]
                    station_el["net"] = key[1]
                else:
                    station_el["lat"] = key[0]
                    station_el["lon"] = key[1]
                    station_el["net"] = key[2]
                for prod_key, prod_value in value.items():
                    if prod_key != "details":
                        product_el = {}
                        if type(prod_key) != tuple:
                            product_el["var"] = prod_key
                            if only_last_data:
                                sorted_values = sorted(
                                    prod_value, key=lambda d: d["ref"], reverse=True
                                )
                                # log.debug(product_el["val"])
                                product_el["val"] = [sorted_values[0]]
                            else:
                                product_el["val"] = prod_value
                            if prod_key not in product_varcodes:
                                product_varcodes.append(prod_key)
                        else:
                            product_el["var"] = prod_key[0]
                            product_el["lev"] = prod_key[1]
                            product_el["trange"] = prod_key[2]
                            product_el["val"] = prod_value
                            if product_el["var"] not in product_varcodes:
                                product_varcodes.append(product_el["var"])
                            if product_el["lev"] not in levels:
                                levels.append(product_el["lev"])
                            if product_el["trange"] not in timeranges:
                                timeranges.append(product_el["trange"])
                        products_list.append(product_el)
                    else:
                        station_el["details"] = prod_value
                        for i in prod_value:
                            if i["var"] not in station_varcodes:
                                station_varcodes.append(i["var"])
                res_el["stat"] = station_el
                res_el["prod"] = products_list
                response_data.append(res_el)

            for el in product_varcodes:
                descr_el = {}
                var_info = dballe.varinfo(el)
                descr_el["descr"] = var_info.desc
                descr_el["unit"] = var_info.unit
                descriptions_dic[el] = descr_el
            for el in station_varcodes:
                descr_el = {}
                var_info = dballe.varinfo(el)
                descr_el["descr"] = var_info.desc
                descriptions_dic[el] = descr_el
            for el in levels:
                descr_el = {}
                descr_el["descr"] = BeDballe.get_description(el, "level")
                descriptions_dic[el] = descr_el
            for el in timeranges:
                descr_el = {}
                descr_el["descr"] = BeDballe.get_description(el, "timerange")
                descriptions_dic[el] = descr_el
        response["descr"] = descriptions_dic
        response["data"] = response_data

        return response

    @staticmethod
    def extend_reftime_for_multimodel(query, db_type, interval=None):
        # check if multiple runs are requested
        if query["datetimemax"] - query["datetimemin"] < timedelta(days=1):
            last_reftime = query["datetimemin"]
        else:
            last_reftime = query["datetimemax"].replace(hour=0, minute=0)
        # change the reftime to according to requested interval
        # or to the multimodel max interval
        if interval:
            new_datetimemax = last_reftime + timedelta(hours=interval)
        else:
            # get multimodel max interval
            explorer = BeDballe.build_explorer(
                db_type, network_list=["multim-forecast"]
            )
            explorer.set_filter({"rep_memo": "multim-forecast"})
            tranges = explorer.tranges
            max_interval: float = 0
            for t in tranges:
                trange_interval = t.p1
                if max_interval:
                    if trange_interval > max_interval:
                        max_interval = trange_interval
                else:
                    max_interval = trange_interval
            new_datetimemax = last_reftime + timedelta(seconds=max_interval)
        return new_datetimemax

    @staticmethod
    def import_data_in_temp_db(db, temp_db, query):
        with db.transaction() as tr:
            with temp_db.transaction() as temptr:
                for cur in tr.query_messages(query):
                    temptr.import_messages(cur.message)

    @staticmethod
    def merge_db_for_download(
        dballe_db,
        dballe_query_data,
        arki_db=None,
        arki_query_data=None,
        mobile_db=None,
        dsn_subset=[],
    ):
        # merge the dbs
        query_data = BeDballe.parse_query_for_maps(dballe_query_data)
        if arki_db:
            log.debug("Filling temp db with data from dballe. query: {}", query_data)
            if not dsn_subset:
                BeDballe.import_data_in_temp_db(dballe_db, arki_db, query_data)
                if mobile_db:
                    BeDballe.import_data_in_temp_db(mobile_db, arki_db, query_data)
            else:
                # get all networks of the requested datasets
                nets = []
                for ds in dsn_subset:
                    for el in arki_service.get_observed_dataset_params(ds):
                        nets.append(el)
                for n in nets:
                    # extract querying network by network
                    query_data["rep_memo"] = n
                    BeDballe.import_data_in_temp_db(dballe_db, arki_db, query_data)
                    # add data extracted from the corresponding dsn for mobile stations
                    if mobile_db:
                        BeDballe.import_data_in_temp_db(mobile_db, arki_db, query_data)
                    # clean the query
                    query_data.pop("rep_memo", None)

        # merge the queries for data
        if arki_query_data:
            if "datetimemin" in arki_query_data:
                query_data["datetimemin"] = arki_query_data["datetimemin"]
        # return the arki_db (the temp one) filled also with data from dballe
        if arki_db:
            return arki_db, query_data
        else:
            return dballe_db, query_data

    @staticmethod
    def download_data_from_map(
        db,
        output_format,
        query_data,
        query_station_data=None,
        qc_filter=False,
        mobile_db=None,
        dsn_subset=[],
    ):
        download_query = {}
        if query_station_data:
            parsed_query = BeDballe.parse_query_for_maps(query_station_data)
        elif query_data:
            parsed_query = BeDballe.parse_query_for_maps(query_data)
        download_query = {**parsed_query}
        if dsn_subset:
            nets = []
            for ds in dsn_subset:
                for el in arki_service.get_observed_dataset_params(ds):
                    nets.append(el)
        with db.transaction() as tr:
            exporter = dballe.Exporter(output_format)
            log.debug("download query: {}", download_query)
            if dsn_subset:
                for n in nets:
                    download_query["rep_memo"] = n
                    for row in tr.query_messages(download_query):
                        if qc_filter:
                            msg = BeDballe.filter_messages(
                                row.message, quality_check=True
                            )
                        else:
                            msg = row.message
                        if msg:
                            yield exporter.to_binary(row.message)
            else:
                for row in tr.query_messages(download_query):
                    if qc_filter:
                        msg = BeDballe.filter_messages(row.message, quality_check=True)
                    else:
                        msg = row.message
                    if msg:
                        yield exporter.to_binary(row.message)
        if mobile_db:
            with mobile_db.transaction() as tr:
                exporter = dballe.Exporter(output_format)
                log.debug("exporting from mobile dsn")
                if dsn_subset:
                    for n in nets:
                        download_query["rep_memo"] = n
                        for row in tr.query_messages(download_query):
                            if qc_filter:
                                msg = BeDballe.filter_messages(
                                    row.message, quality_check=True
                                )
                            else:
                                msg = row.message
                            if msg:
                                yield exporter.to_binary(row.message)
                else:
                    for row in tr.query_messages(download_query):
                        if qc_filter:
                            msg = BeDballe.filter_messages(
                                row.message, quality_check=True
                            )
                        else:
                            msg = row.message
                        if msg:
                            yield exporter.to_binary(row.message)

    @staticmethod
    def from_query_to_dic(q):
        # example of query string: string= "reftime: >=2020-02-01 01:00,<=2020-02-04 15:13;level:1,0,0,0 or 103,2000,0,0;product:B11001 or B13011;timerange:0,0,3600 or 1,0,900;network:fidupo or agrmet"
        params_list = ["reftime", "network", "product", "level", "timerange", "license"]
        query_list = q.split(";")
        query_dic: Dict[str, Any] = {}
        for e in query_list:
            for p in params_list:
                if e.startswith(p):
                    val = e.split(p + ":")[1]
                    # ex. from 'level:1,0,0,0 or 103,2000,0,0' to '1,0,0,0 or 103,2000,0,0'

                    # reftime param has to be parsed differently
                    if p == "reftime":
                        reftimes = [x.strip() for x in val.split(",")]
                        # ex. from ' >=2020-02-01 01:00,<=2020-02-04 15:13' to ['>=2020-02-01 01:00', '<=2020-02-04 15:13']
                        for r in reftimes:
                            if r.startswith(">"):
                                date_min = r.strip(">=")
                                query_dic["datetimemin"] = dateutil.parser.parse(
                                    date_min
                                )
                            if r.startswith("<"):
                                date_max = r.strip("<=")
                                query_dic["datetimemax"] = dateutil.parser.parse(
                                    date_max
                                )
                            if r.startswith("="):
                                date = r.strip("=")
                                query_dic["datetimemin"] = query_dic[
                                    "datetimemax"
                                ] = dateutil.parser.parse(date)

                    # parsing all other parameters
                    elif p == "license":
                        query_dic[p] = val
                    else:
                        val_list = [x.strip() for x in val.split(" or ")]
                        query_dic[p] = val_list
        return query_dic

    @staticmethod
    def from_level_object_to_string(level):
        level_list = []

        if level.ltype1:
            ltype1 = str(level.ltype1)
        else:
            ltype1 = "0"
        level_list.append(ltype1)

        if level.l1:
            l1 = str(level.l1)
        else:
            l1 = "0"
        level_list.append(l1)

        if level.ltype2:
            ltype2 = str(level.ltype2)
        else:
            ltype2 = "0"
        level_list.append(ltype2)

        if level.l2:
            l2 = str(level.l2)
        else:
            l2 = "0"
        level_list.append(l2)

        level_parsed = ",".join(level_list)
        return level_parsed

    @staticmethod
    def from_trange_object_to_string(trange):
        trange_list = []

        pind = str(trange.pind)
        trange_list.append(pind)

        p1 = str(trange.p1)
        trange_list.append(p1)

        p2 = str(trange.p2)
        trange_list.append(p2)

        trange_parsed = ",".join(trange_list)
        return trange_parsed

    @staticmethod
    def from_list_of_params_to_list_of_dic(param_list, type):
        list_dic = []
        for p in param_list:
            item = {}
            item["code"] = p
            if type == "network":
                # get the dataset description instead of the dballe one
                dataset_id = arki_service.from_network_to_dataset(p)
                alchemy_db = sqlalchemy.get_instance()
                dataset = alchemy_db.Datasets.query.filter_by(
                    arkimet_id=dataset_id
                ).first()
                if dataset:
                    item["desc"] = dataset.name
                    item["longdesc"] = dataset.description
                else:
                    item["desc"] = BeDballe.get_description(p, type)
            else:
                item["desc"] = BeDballe.get_description(p, type)
            list_dic.append(item)
        return list_dic

    @staticmethod
    def get_description(value, type):
        if type == "network":
            description = value
        elif type == "product":
            var_code = value
            var_infos = dballe.varinfo(var_code)
            description = var_infos.desc
        elif type == "timerange" or type == "level":
            list: List[Optional[int]] = []
            for v in value.split(","):
                if type == "level" and v == "0":
                    val = None
                    list.append(val)
                else:
                    list.append(int(v))
            if type == "timerange":
                tr = dballe.Trange(list[0], list[1], list[2])
                description = tr.describe()
            else:
                lev = dballe.Level(list[0], list[1], list[2], list[3])
                description = lev.describe()

        return description

    @staticmethod
    def parse_query_for_maps(query):
        query_data = {}
        # now parse query does not support multiple values for a single param. This use case is supported by maps_observed api instead
        # adapt the query to the dballe syntax and add the params to the general query
        to_parse = [
            "level",
            "network",
            "product",
            "timerange",
            "datetimemin",
            "datetimemax",
        ]
        dballe_keys = [
            "level",
            "rep_memo",
            "var",
            "trange",
            "datetimemin",
            "datetimemax",
        ]
        allowed_keys = [
            "lonmin",
            "lonmax",
            "latmin",
            "latmax",
            "query",
            "lat",
            "lon",
            "ident",
            "rep_memo",
        ]
        for key, value in query.items():
            if key in to_parse:
                key_index = to_parse.index(key)
                if (
                    key == "timerange"
                    or key == "level"
                    and not isinstance(value, tuple)
                ):
                    tuple_list: List[Optional[int]] = []
                    for v in value[0].split(","):
                        if key == "level" and v == "0":
                            val = None
                            tuple_list.append(val)
                        else:
                            tuple_list.append(int(v))
                    query_data[dballe_keys[key_index]] = tuple(tuple_list)
                else:
                    if not isinstance(value, list):
                        query_data[dballe_keys[key_index]] = value
                    else:
                        query_data[dballe_keys[key_index]] = value[0]
            elif key in allowed_keys or key in dballe_keys:
                query_data[key] = value
        return query_data

    @staticmethod
    def from_filters_to_lists(filters):
        fields = []
        queries = []
        allowed_keys = ["level", "network", "product", "timerange"]
        dballe_keys = ["level", "rep_memo", "var", "trange"]

        for key, value in filters.items():
            if key in allowed_keys:
                # change the key name from model to dballe name
                key_index = allowed_keys.index(key)
                fields.append(dballe_keys[key_index])

                field_queries = []
                for e in value:
                    if key == "timerange" or key == "level":
                        # transform the timerange or level value in a tuple
                        # (required for dballe query)
                        tuple_list: List[Optional[int]] = []
                        for v in e["code"].split(","):
                            if key == "level" and v == "0":
                                val = None
                                tuple_list.append(val)
                            else:
                                tuple_list.append(int(v))
                        field_queries.append(tuple(tuple_list))
                    else:
                        field_queries.append(e["code"])
                queries.append(field_queries)
            else:
                continue

        return fields, queries

    @staticmethod
    def from_query_to_lists(query):
        fields = []
        queries = []
        allowed_keys = [
            "level",
            "network",
            "product",
            "timerange",
            "datetimemin",
            "datetimemax",
            "ana_id",
            "latmin",
            "lonmin",
            "latmax",
            "lonmax",
        ]
        dballe_keys = [
            "level",
            "rep_memo",
            "var",
            "trange",
            "datetimemin",
            "datetimemax",
            "ana_id",
            "latmin",
            "lonmin",
            "latmax",
            "lonmax",
        ]

        for key, value in query.items():
            if key in allowed_keys:
                # log.debug('{}: {}',key,value)
                # change the key name from model to dballe name
                key_index = allowed_keys.index(key)
                fields.append(dballe_keys[key_index])
                if key == "timerange" or key == "level":
                    # transform the timerange or level value in a tuple
                    # (required for dballe query)
                    query_list = []
                    for v in value:
                        split_list = v.split(",")
                        tuple_list: List[Optional[int]] = []
                        for s in split_list:
                            if key == "level" and s == "0":
                                val = None
                                tuple_list.append(val)
                            else:
                                tuple_list.append(int(s))
                        query_list.append(tuple(tuple_list))
                    queries.append(query_list)
                elif key == "datetimemin" or key == "datetimemax":
                    query_list = []
                    query_list.append(value)
                    queries.append(query_list)
                else:
                    if isinstance(value, list):
                        queries.append(value)
                    else:
                        queries.append([value])
            else:
                continue
        return fields, queries

    @staticmethod
    def parse_data_extraction_reftime(from_str, to_str):
        from_dt = dateutil.parser.parse(from_str)
        to_dt = dateutil.parser.parse(to_str)

        # to prevent problems with timezones
        from_naive = from_dt.replace(tzinfo=None)
        to_naive = to_dt.replace(tzinfo=None)

        return from_naive, to_naive

    @staticmethod
    def from_datetime_to_list(dt):
        str = dt.strftime("%Y,%m,%d,%H,%M,%S")
        str_list = str.split(",")
        list = []
        for s in str_list:
            list.append(int(s))
        return list

    @staticmethod
    def fill_db_from_arkimet(datasets, query):
        log.debug("filling dballe with data from arkimet")
        db = dballe.DB.connect("mem:")
        cfg = arki.cfg.Sections.parse(arki_service.arkimet_conf)
        importer = dballe.Importer("BUFR")
        with tempfile.SpooledTemporaryFile(mode="a+b", max_size=10000000) as tmpf:
            for d in datasets:
                dt_part = cfg.section(d)
                source = arki.dataset.Session().dataset_reader(cfg=dt_part)
                bin_data = source.query_bytes(query, with_data=True)
                tmpf.write(bin_data)
            tmpf.seek(0)
            with dballe.File(tmpf, "BUFR") as f:
                for binmsg in f:
                    msgs = importer.from_binary(binmsg)
                    with db.transaction() as tr:
                        tr.import_messages(msgs)
        return db

    @staticmethod
    def parse_query_for_data_extraction(datasets, filters=None, reftime=None):
        # get network list from requested datasets
        dataset_nets = []
        for ds in datasets:
            nets = arki_service.get_observed_dataset_params(ds)
            for n in nets:
                dataset_nets.append(n)

        fields = []
        queries = []
        # create a "base" query using the filters
        if filters:
            fields, queries = BeDballe.from_filters_to_lists(filters)
            # check if requested networks are in that dataset
            if "rep_memo" in fields:
                key_index = fields.index("rep_memo")
                nets_in_query = queries[key_index]
                if not all(elem in dataset_nets for elem in nets_in_query):
                    raise InvalidFiltersException(
                        "Failure in data extraction: Invalid set of filters"
                    )

        # parsing reftime and add it to the query
        if reftime:
            date_min, date_max = BeDballe.parse_data_extraction_reftime(
                reftime["from"], reftime["to"]
            )
            fields.append("datetimemin")
            queries.append([date_min])
            fields.append("datetimemax")
            queries.append([date_max])

        # if there aren't filters, data are filtered only by dataset's networks
        if "rep_memo" not in fields:
            fields.append("rep_memo")
            queries.append(dataset_nets)

        return fields, queries

    @staticmethod
    def extract_data_for_mixed(
        datasets, fields, queries, outfile, queried_reftime=None
    ):
        # extract data from the dballe database
        log.debug("mixed dbs: extract data from dballe")
        dballe_queries = []
        for q in queries:
            dballe_queries.append(q)
        additional_runs = None
        if "datetimemin" in fields:
            (
                refmax_dballe,
                refmin_dballe,
                refmax_arki,
                refmin_arki,
            ) = BeDballe.split_reftimes(
                queries[fields.index("datetimemin")][0],
                queries[fields.index("datetimemax")][0],
            )
            if queried_reftime:
                # multimodel case, the datemin has to coincide with a run
                refmin_dballe = refmin_dballe.replace(hour=0, minute=0)
                # calculate the number of requested runs to add for dballe extraction
                date_delta = (refmin_dballe - refmin_arki).days
                if date_delta > 4:
                    additional_runs = 4
                else:
                    additional_runs = date_delta
            # set up query for dballe with the correct reftimes
            dballe_queries[fields.index("datetimemin")][0] = refmin_dballe

        dballe_outfile = Path(f"{outfile}_dballe_part.tmp")

        # extract
        BeDballe.extract_data(
            datasets,
            fields,
            dballe_queries,
            dballe_outfile,
            db_type="dballe",
            queried_reftime=queried_reftime,
            additional_runs=additional_runs,
            mixed_extraction=True,
        )

        # extract data from the arkimet database
        log.debug("mixed dbs: extract data from arkimet")
        arki_queries = []
        for q in queries:
            arki_queries.append(q)
        if "datetimemin" in fields:
            # set up query for arkimet with the correct reftimes
            arki_queries[fields.index("datetimemin")][0] = refmin_arki
            arki_queries[fields.index("datetimemax")][0] = refmax_arki

        arki_outfile = Path(f"{outfile}_arki_part.tmp")

        # extract
        queried_reftime_for_arki = None
        if queried_reftime:
            # use il reftime arki as queried reftime
            queried_reftime_for_arki = refmax_arki
        BeDballe.extract_data(
            datasets,
            fields,
            arki_queries,
            arki_outfile,
            db_type="arkimet",
            queried_reftime=queried_reftime_for_arki,
            mixed_extraction=True,
        )

        cat_cmd = ["cat"]
        if dballe_outfile.exists():
            cat_cmd.append(str(dballe_outfile))
        if arki_outfile.exists():
            cat_cmd.append(str(arki_outfile))

        # check if the extractions were done
        if len(cat_cmd) == 1:
            # any extraction file exists
            raise EmptyOutputFile(
                "Failure in data extraction: the query does not give any result"
            )

        # join the dballe extraction with the arki one
        with open(outfile, mode="w") as output:
            ext_proc = subprocess.Popen(cat_cmd, stdout=output)
            ext_proc.wait()
            if ext_proc.wait() != 0:
                raise JoinObservedExtraction(
                    "Failure in data extraction: error in creating the output file for mixed archives"
                )

        # delete the partial extractions
        for f in cat_cmd:
            if Path(f).is_file():
                Path(f).unlink()

    @staticmethod
    def extract_data(
        datasets,
        fields,
        queries,
        outfile,
        db_type,
        queried_reftime=None,
        additional_runs=None,
        mixed_extraction=False,
    ):
        # get the license group
        alchemy_db = sqlalchemy.get_instance()
        engine = alchemy_db.variables.get("dbtype")
        user = alchemy_db.variables.get("user")
        pw = alchemy_db.variables.get("password")
        host = alchemy_db.variables.get("host")
        port = alchemy_db.variables.get("port")
        license_group = SqlApiDbManager.get_license_group(alchemy_db, datasets)
        # choose the db
        arkimet_query = None
        if db_type == "arkimet":
            # create arkimet query
            network = None
            if "rep_memo" in fields:
                network = queries[fields.index("rep_memo")]

            datemin = None
            datemax = None
            if "datetimemin" in fields:
                datemin = queries[fields.index("datetimemin")][0].strftime(
                    "%Y-%m-%d %H:%M"
                )
                datemax = queries[fields.index("datetimemax")][0].strftime(
                    "%Y-%m-%d %H:%M"
                )

            # get all the possible combinations of queries
            all_queries = list(itertools.product(*queries))
            arkimet_query = BeDballe.build_arkimet_query(
                datemin=datemin,
                datemax=datemax,
                network=network,
                all_dballe_queries=all_queries,
                fields=fields,
                license_group=license_group,
            )
            if not arkimet_query:
                if mixed_extraction:
                    # break the extraction in order not to create the output file
                    return
                else:
                    raise EmptyOutputFile(
                        "Failure in data extraction: the query does not give any result"
                    )

            # log.debug(f" arkimet query: {arkimet_query}")
            DB = BeDballe.fill_db_from_arkimet(datasets, arkimet_query)

        else:
            # get the dsn
            dballe_dsn = license_group.dballe_dsn
            try:
                DB = dballe.DB.connect(
                    f"{engine}://{user}:{pw}@{host}:{port}/{dballe_dsn}"
                )
            except OSError:
                raise OSError("Unable to connect to dballe database")
        requested_runs = []
        if queried_reftime:
            # multimodel case. get a list of all runs
            total_runs = queried_reftime - queries[fields.index("datetimemin")][0]
            n_total_runs = total_runs.days
            # if not n_total_runs:
            #     # only one run is requested
            #     n_total_runs = 1
            for i in range(n_total_runs + 1):
                multim_run = queries[fields.index("datetimemin")][0] + timedelta(days=i)
                if not queries[fields.index("datetimemin")][0] == multim_run:
                    # be sure that all runs are 00:00
                    requested_runs.append(
                        multim_run.replace(hour=0, minute=0, second=0, microsecond=0)
                    )
                else:
                    requested_runs.append(multim_run)
            # mixed db case: add the requested runs that are supposed to be in arkimet
            if additional_runs:
                for i in range(additional_runs + 1):
                    multim_run = queries[fields.index("datetimemin")][0] - timedelta(
                        days=i
                    )
                    if not queries[fields.index("datetimemin")][0] == multim_run:
                        # be sure that all runs are 00:00
                        requested_runs.append(
                            multim_run.replace(
                                hour=0, minute=0, second=0, microsecond=0
                            )
                        )
            log.debug("requested runs: {}", requested_runs)
        # get all the possible combinations of queries
        all_queries = list(itertools.product(*queries))
        counter = 1
        cat_cmd = ["cat"]
        for q in all_queries:
            dballe_query = {}
            for k, v in zip(fields, q):
                dballe_query[k] = v

            # set the filename for the partial extraction
            part_outfile = f"{outfile}_part{counter}.tmp"

            with DB.transaction() as tr:
                # check if the query gives a result
                count = tr.query_data(dballe_query).remaining
                # log.debug(
                #     "counter = {} dballe query: {} count: {}",
                #     counter, dballe_query, count
                # )
                if count == 0:
                    continue
                log.debug("Extract data from dballe. query: {}", dballe_query)
                exporter = dballe.Exporter("BUFR")
                with open(part_outfile, "wb") as out:
                    for row in tr.query_messages(dballe_query):
                        if queried_reftime:
                            msg = BeDballe.filter_messages(
                                row.message, list_of_runs=requested_runs
                            )
                        else:
                            msg = row.message
                        if msg:
                            out.write(exporter.to_binary(msg))

            cat_cmd.append(part_outfile)
            # update counter
            counter += 1

        if db_type == "arkimet":
            # clear the temporary db
            DB.remove_all()

        if counter == 1:
            # any query has given a result
            if mixed_extraction:
                return
            else:
                raise EmptyOutputFile(
                    "Failure in data extraction: the query does not give any result"
                )

        # join all the partial extractions
        with open(outfile, mode="w") as output:
            ext_proc = subprocess.Popen(cat_cmd, stdout=output)
            ext_proc.wait()
            if ext_proc.wait() != 0:
                raise JoinObservedExtraction(
                    "Failure in data extraction: error in creating the output file"
                )
        # delete the partial extractions
        for f in cat_cmd:
            if Path(f).is_file():
                Path(f).unlink()

    @staticmethod
    def filter_messages(msg, list_of_runs=None, quality_check=False):
        count_msgs = 0
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

        for data in msg.query_data({"query": "attrs"}):
            variable = data["variable"]
            attrs = variable.get_attrs()
            v = dballe.var(data["variable"].code, data["variable"].get())
            to_be_discarded = False
            # 1.Multimodel filter
            if list_of_runs:
                for a in attrs:
                    v.seta(a)

                # get the validity interval from the data timerange
                validity_interval = timedelta(seconds=data["trange"].p1)
                # get the message date
                validity_time = datetime(
                    msg.get_named("year").get(),
                    msg.get_named("month").get(),
                    msg.get_named("day").get(),
                    msg.get_named("hour").get(),
                    msg.get_named("minute").get(),
                )
                # compare the resulting reftime with the list of run
                if not validity_time - validity_interval in list_of_runs:
                    to_be_discarded = True
            # 2. Quality control filter
            if quality_check:
                is_ok = BeDballe.data_qc(attrs)
                if not is_ok:
                    to_be_discarded = True
            if not to_be_discarded:
                # if matches proceed saving the message
                new_msg.set(data["level"], data["trange"], v)
                count_msgs += 1
            else:
                continue

        for data in msg.query_station_data({"query": "attrs"}):
            variable = data["variable"]
            attrs = variable.get_attrs()
            v = dballe.var(data["variable"].code, data["variable"].get())
            for a in attrs:
                v.seta(a)

            new_msg.set(dballe.Level(), dballe.Trange(), v)
        if count_msgs > 0:
            # there are matching messages:
            # return the filtered message in order to be exported
            return new_msg
        else:
            return None

    @staticmethod
    def is_query_for_pluvio_aggregations(query_dict):
        """
        Returns the specific dballe dsn for aggregated pluvio data.
        """
        dsn = None
        if "product" and "timerange" in query_dict:
            if (
                query_dict["product"][0] == "B13011"
                and query_dict["timerange"][0] in BeDballe.AGGREGATIONS_TRANGES
            ):
                dsn = BeDballe.AGGREGATIONS_DSN
        return dsn

    @staticmethod
    def get_queries_and_dsn_list_with_itertools(original_query):
        # check if there are filters with multiple queries
        single_params = {}
        list_params = {}
        query_and_dsn_list: Optional[List[Dict[str, Any]]] = []
        for k, v in original_query.items():
            if not isinstance(v, list) or len(v) == 1:
                single_params[k] = v
            else:
                list_params[k] = v
        if not list_params:
            # not multiple queries, append the original query to the query list
            dsn = BeDballe.is_query_for_pluvio_aggregations(single_params)
            query_and_dsn_list.append({"query": single_params, "aggregations_dsn": dsn})
        else:
            # prepare the multiple queries
            fields = []
            queries = []
            for k, v in list_params.items():
                fields.append(k)
                queries.append(v)
            all_queries = list(itertools.product(*queries))
            for q in all_queries:
                single_query = {**single_params}
                for k, v in zip(fields, q):
                    single_query[k] = [v]
                dsn = BeDballe.is_query_for_pluvio_aggregations(single_query)
                query_and_dsn_list.append(
                    {"query": single_query, "aggregations_dsn": dsn}
                )

        return query_and_dsn_list
