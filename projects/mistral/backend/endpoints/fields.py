from datetime import datetime

from mistral.exceptions import AccessToDatasetDenied
from mistral.services.arkimet import BeArkimet as arki
from mistral.services.dballe import BeDballe as dballe
from restapi import decorators
from restapi.exceptions import RestApiException
from restapi.models import InputSchema, UniqueDelimitedList, fields
from restapi.rest.definition import EndpointResource
from restapi.utilities.htmlcodes import hcodes
from restapi.utilities.logs import log


class FieldsQuery(InputSchema):
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

    @decorators.auth.require()
    @decorators.use_kwargs(FieldsQuery)
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
                raise RestApiException(
                    "Coordinates for bounding box are missing",
                    status_code=hcodes.HTTP_BAD_REQUEST,
                )
            else:
                bounding_box["lonmin"] = lonmin
                bounding_box["lonmax"] = lonmax
                bounding_box["latmin"] = latmin
                bounding_box["latmax"] = latmax

        # check for existing dataset(s)
        if datasets:
            for ds_name in datasets:
                found = next(
                    (ds for ds in arki.load_datasets() if ds.get("id", "") == ds_name),
                    None,
                )
                if not found:
                    raise RestApiException(
                        f"Dataset '{ds_name}' not found",
                        status_code=hcodes.HTTP_BAD_NOTFOUND,
                    )

            data_type = arki.get_datasets_category(datasets)
            if not data_type:
                raise RestApiException(
                    "Invalid set of datasets : datasets categories are different",
                    status_code=hcodes.HTTP_BAD_REQUEST,
                )
        else:
            # if data_type is forecast always dataset has to be specified.
            # If dataset is not in query data_type can't be 'FOR'
            data_type = "OBS"

        # ######### OBSERVED DATA ###########
        if data_type == "OBS":
            summary = None
            log.debug(f"Dataset(s) for observed data: {datasets}")

            resulting_fields = {"summarystats": {"c": 0, "s": 0}}
            requested_nets = []
            # check db type
            query_dic = {}
            if q:
                query_dic = dballe.from_query_to_dic(q)
            if bounding_box:
                for key, value in bounding_box.items():
                    query_dic[key] = value
            if "datetimemin" in query_dic:
                db_type = dballe.get_db_type(
                    query_dic["datetimemin"], query_dic["datetimemax"]
                )
            else:
                db_type = "mixed"
            log.debug("db type: {}", db_type)

            if datasets:
                # get dataset pars to filter dballe according to the requested dataset
                for ds in datasets:
                    ds_params = arki.get_observed_dataset_params(ds)
                    for net in ds_params:
                        requested_nets.append(net)
                    log.info(f"dataset: {ds}, networks: {ds_params}")
                    try:
                        if db_type == "mixed":
                            fields, summary = dballe.load_filter_for_mixed(
                                datasets,
                                ds_params,
                                SummaryStats,
                                allAvailableProducts,
                                query=query_dic,
                            )
                        else:
                            fields, summary = dballe.load_filters(
                                datasets,
                                ds_params,
                                SummaryStats,
                                allAvailableProducts,
                                db_type=db_type,
                                query_dic=query_dic,
                            )
                    except AccessToDatasetDenied:
                        raise RestApiException(
                            "Access to dataset denied",
                            status_code=hcodes.HTTP_SERVER_ERROR,
                        )
                    if not fields:
                        continue
                    else:
                        for key in fields:
                            # check and integrate the filter dic
                            if key not in resulting_fields:
                                resulting_fields[key] = fields[key]
                            else:
                                # merge the two lists
                                resulting_fields[key].extend(
                                    x
                                    for x in fields[key]
                                    if x not in resulting_fields[key]
                                )
                        # update the summary
                        if SummaryStats:
                            resulting_fields["summarystats"]["c"] += summary["c"]
                            if "e" not in resulting_fields["summarystats"]:
                                resulting_fields["summarystats"]["e"] = summary["e"]
                            else:
                                summary_date = datetime(
                                    *resulting_fields["summarystats"]["e"]
                                )
                                new_date = datetime(*summary["e"])
                                if new_date > summary_date:
                                    resulting_fields["summarystats"]["e"] = summary["e"]
                            if "b" not in resulting_fields["summarystats"]:
                                resulting_fields["summarystats"]["b"] = summary["b"]
                            else:
                                summary_date = datetime(
                                    *resulting_fields["summarystats"]["b"]
                                )
                                new_date = datetime(*summary["b"])
                                if new_date < summary_date:
                                    resulting_fields["summarystats"]["b"] = summary["b"]
            else:
                ds_params = []
                if db_type == "mixed":
                    fields, summary = dballe.load_filter_for_mixed(
                        datasets,
                        ds_params,
                        SummaryStats,
                        allAvailableProducts,
                        query=query_dic,
                    )
                else:
                    fields, summary = dballe.load_filters(
                        datasets,
                        ds_params,
                        SummaryStats,
                        allAvailableProducts,
                        db_type=db_type,
                        query_dic=query_dic,
                    )
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
                raise RestApiException(
                    "Access to dataset denied", status_code=hcodes.HTTP_SERVER_ERROR,
                )

        # ######### ONLY ARKIMET SUMMARY ###########
        if onlySummaryStats:
            # we want to return ONLY summary Stats with no fields
            log.debug("ONLY Summary Stats")
            summary = summary["items"]["summarystats"]
        if not SummaryStats:
            log.debug("not summary")
            resulting_fields.pop("summarystats", None)
        return self.response(summary)
