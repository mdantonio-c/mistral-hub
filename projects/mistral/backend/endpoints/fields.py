from mistral.exceptions import AccessToDatasetDenied
from mistral.services.arkimet import BeArkimet as arki
from mistral.services.dballe import BeDballe as dballe
from mistral.services.sqlapi_db_manager import SqlApiDbManager
from restapi import decorators
from restapi.connectors import sqlalchemy
from restapi.exceptions import BadRequest, NotFound, ServerError, Unauthorized
from restapi.models import Schema, UniqueDelimitedList, fields
from restapi.rest.definition import EndpointResource
from restapi.utilities.logs import log


class FieldsQuery(Schema):
    datasets = UniqueDelimitedList(fields.Str(), delimiter=",")
    q = fields.Str(required=False)
    lonmin = fields.Float(required=False)
    latmin = fields.Float(required=False)
    lonmax = fields.Float(required=False)
    latmax = fields.Float(required=False)
    onlySummaryStats = fields.Bool(required=False)
    SummaryStats = fields.Bool(required=False)
    allAvailableProducts = fields.Bool(required=False)


class Fields(EndpointResource):

    labels = ["field"]

    @decorators.auth.optional()
    @decorators.use_kwargs(FieldsQuery, location="query")
    @decorators.endpoint(
        path="/fields",
        summary="Get summary fields for given dataset(s).",
        responses={200: "List of fields successfully retrieved"},
    )
    # 200: {'schema': {'$ref': '#/definitions/Summary'}}
    def get(
        self,
        datasets=[],
        q="",
        lonmin=None,
        latmin=None,
        lonmax=None,
        latmax=None,
        onlySummaryStats=False,
        SummaryStats=True,
        allAvailableProducts=False,
    ):
        """ Get all fields for given datasets"""
        bounding_box = {}
        if lonmin:
            if not lonmax or not latmin or not latmax:
                raise BadRequest("Coordinates for bounding box are missing")
            else:
                bounding_box["lonmin"] = lonmin
                bounding_box["lonmax"] = lonmax
                bounding_box["latmin"] = latmin
                bounding_box["latmax"] = latmax

        # check for existing dataset(s)
        user = self.get_user()
        db = sqlalchemy.get_instance()
        if datasets:
            if not user:
                # case of data extraction: endpoint needs authorization
                raise Unauthorized(
                    "to access this functionality the user has to be logged"
                )
            for ds_name in datasets:
                found = next(
                    (
                        ds
                        for ds in SqlApiDbManager.get_datasets(db, user)
                        if ds.get("id", "") == ds_name
                    ),
                    None,
                )
                if not found:
                    raise NotFound(
                        f"Dataset '{ds_name}' not found: check for dataset name of for your authorizations"
                    )

            if len(datasets) > 1 and "multim-forecast" in datasets:
                raise BadRequest(
                    "selection multi-dataset for multimodel forecast is not supported yet"
                )

            data_type = arki.get_datasets_category(datasets)
            if not data_type:
                raise BadRequest(
                    "Invalid set of datasets : datasets categories are different"
                )
        else:
            # maps case: TODO: manage user authorizations
            # if data_type is forecast always dataset has to be specified.
            # If dataset is not in query data_type can't be 'FOR'
            data_type = "OBS"

        # ######### OBSERVED DATA ###########
        if data_type == "OBS" or "multim-forecast" in datasets:
            summary = None
            log.debug(f"Dataset(s) for observed data: {datasets}")

            resulting_fields = {"summarystats": {"c": 0, "s": 0}}
            # check db type
            query_dic = {}
            if q:
                query_dic = dballe.from_query_to_dic(q)
            if bounding_box:
                for key, value in bounding_box.items():
                    query_dic[key] = value

            queried_reftime = None
            if "datetimemin" in query_dic:
                db_type = dballe.get_db_type(
                    query_dic["datetimemin"], query_dic["datetimemax"]
                )
                if "network" in query_dic and "multim-forecast" in query_dic["network"]:
                    # multimodel case: extend reftime
                    # check if an interval is requested
                    interval = None
                    if "timerange" in query_dic:
                        splitted_timerange = query_dic["timerange"][0].split(",")
                        interval = int(splitted_timerange[1]) / 3600
                    queried_reftime = query_dic["datetimemax"]
                    query_dic["datetimemax"] = dballe.extend_reftime_for_multimodel(
                        query_dic, db_type, interval=interval
                    )
                    if db_type == "arkimet":
                        # check if db_type is changed (from arkimet to mixed) with the extended query
                        db_type = dballe.get_db_type(
                            query_dic["datetimemin"], query_dic["datetimemax"]
                        )

                if db_type != "dballe" and not user:
                    raise Unauthorized(
                        "to access archived data the user has to be logged"
                    )
            else:
                if not user:
                    raise Unauthorized(
                        "to access archived data the user has to be logged"
                    )
                else:
                    db_type = "mixed"
            log.debug("db type: {}", db_type)

            # TODO check unique license
            ds_params = []
            if datasets:
                # get dataset pars to filter dballe according to the requested dataset
                for ds in datasets:
                    for el in arki.get_observed_dataset_params(ds):
                        ds_params.append(el)
                    log.info(f"dataset: {ds}, networks: {ds_params}")
            try:
                fields, summary = dballe.load_filters(
                    ds_params,
                    SummaryStats,
                    allAvailableProducts,
                    db_type=db_type,
                    query_dic=query_dic,
                    queried_reftime=queried_reftime,
                )
            except AccessToDatasetDenied:
                raise ServerError("Access to dataset denied")

            if fields:
                for key in fields:
                    resulting_fields[key] = fields[key]
                if SummaryStats:
                    for key in summary:
                        resulting_fields["summarystats"][key] = summary[key]

            summary = {"items": resulting_fields}

        # ######### ARKIMET ###########
        else:
            try:
                summary = arki.load_summary(datasets, q)
            except AccessToDatasetDenied:
                raise ServerError("Access to dataset denied")

        # ######### ONLY ARKIMET SUMMARY ###########
        if onlySummaryStats:
            # we want to return ONLY summary Stats with no fields
            log.debug("ONLY Summary Stats")
            summary = summary["items"]["summarystats"]
        if not SummaryStats:
            log.debug("not summary")
            resulting_fields.pop("summarystats", None)
        return self.response(summary)
