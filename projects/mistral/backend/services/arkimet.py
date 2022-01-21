import io
import json
import math
import shlex
import subprocess

import arkimet as arki
import dateutil.parser
from arkimet.cfg import Sections
from mistral.exceptions import AccessToDatasetDenied
from restapi.env import Env
from restapi.utilities.logs import log

DATASET_ROOT = Env.get("DATASET_ROOT", "/")


class BeArkimet:

    allowed_filters = (
        "area",
        "level",
        "origin",
        "proddef",
        "product",
        "quantity",
        "run",
        "task",
        "timerange",
        "network",
    )

    allowed_processors = ("additional_variables",)
    allowed_licenses = ("CCBY4.0", "CCBY-SA4.0")
    arkimet_conf = "/arkimet/config/arkimet.conf"

    @staticmethod
    def load_datasets():
        """
        Load datasets by parsing arkimet.conf

        :return: list of datasets
        """
        datasets = []
        cfg_sections = Sections()
        cfg = cfg_sections.parse(BeArkimet.arkimet_conf)
        for i in [a for a in cfg.items() if a[0] not in ["error", "duplicates"]]:
            ds = {"id": i[0]}
            for k, v in i[1].items():
                if "_name" in i[1]:
                    name_key = "_name"
                else:
                    name_key = "name"
                if k == name_key:
                    ds["name"] = v
                elif k == "description":
                    ds["description"] = v
                elif k == "_license":
                    ds["license"] = v
                elif k == "_category":
                    ds["category"] = v
                elif k == "format":
                    ds["format"] = v
                elif k == "bounding":
                    ds["bounding"] = v
                elif k == "_attribution":
                    ds["attribution"] = v
            datasets.append(ds)
        return datasets

    @staticmethod
    def load_summary(datasets=[], query=""):
        """
        Get summary for one or more datasets. If no dataset is provided consider all available ones.
        :param datasets: List of datasets
        :param query: Optional arkimet query filter
        :return:
        """

        if query is None:
            query = ""

        # parse the config
        cfg_sections = Sections()
        cfg = cfg_sections.parse(BeArkimet.arkimet_conf)

        summary = ""
        arki_summary = None
        # add the datasets to a session
        with arki.dataset.Session() as session:
            for name, section in cfg.items():
                if datasets:
                    # add the selected datasets to the session
                    if name in datasets:
                        log.debug(f"added {name}")
                        session.add_dataset(section)
                else:
                    # add all datasets to the section
                    log.debug(f"added {name}")
                    session.add_dataset(section)
            # use Session.merged() to see all the selected datasets as it is one
            with session.merged() as dataset:
                with dataset.reader() as reader:
                    # import query
                    matcher = session.matcher(query)
                    log.debug(f"query: {query}")
                    # ask the summary
                    arki_summary = reader.query_summary(matcher)

        if arki_summary:
            with io.BytesIO() as out:
                arki_summary.write_short(out, format="json", annotate=True)
                out.seek(0)
                summary = json.load(out)

        return summary

    @staticmethod
    def estimate_data_size(datasets, query):
        """
        Estimate arki-query output size.
        """
        cfg = arki.cfg.Sections.parse(BeArkimet.arkimet_conf)
        summary = arki.Summary()
        for d in datasets:
            dt = cfg.section(d)
            source = arki.dataset.Session().dataset_reader(cfg=dt)
            source.query_summary(query, summary)

        return summary.size

    @staticmethod
    def is_filter_allowed(filter_name):
        return True if filter_name in BeArkimet.allowed_filters else False

    @staticmethod
    def is_processor_allowed(processor_name):
        return True if processor_name in BeArkimet.allowed_processors else False

    @staticmethod
    def parse_reftime(from_str, to_str):
        """
        Return Arkimet reftime query
        :param from_str: ISO8610 date-time
        :type from_str: string
        :param to_str: ISO8610 date-time
        :type to_str: string
        :return: Arkimet query for reftime
        """
        from_dt = dateutil.parser.parse(from_str)
        to_dt = dateutil.parser.parse(to_str)

        gt = from_dt.strftime("%Y-%m-%d %H:%M")
        lt = to_dt.strftime("%Y-%m-%d %H:%M")
        return f"reftime: >={gt},<={lt}"

    @staticmethod
    def parse_matchers(filters):
        """
        Parse incoming filters and return an arkimet query.
        :param filters:
        :return:
        """
        matchers = []
        for k in filters:
            values = filters[k]
            if not isinstance(values, list):
                values = [values]
            log.debug(values)
            if k == "area":
                q = " or ".join([BeArkimet.__decode_area(i) for i in values])
            elif k == "level":
                q = " or ".join([BeArkimet.__decode_level(i) for i in values])
            elif k == "origin":
                q = " or ".join([BeArkimet.__decode_origin(i) for i in values])
            elif k == "proddef":
                q = " or ".join([BeArkimet.__decode_proddef(i) for i in values])
            elif k == "product":
                q = " or ".join([BeArkimet.__decode_product(i) for i in values])
            elif k == "quantity":
                q = " or ".join([BeArkimet.__decode_quantity(i) for i in values])
            elif k == "run":
                q = " or ".join([BeArkimet.decode_run(i) for i in values])
            elif k == "task":
                q = " or ".join([BeArkimet.__decode_task(i) for i in values])
            elif k == "timerange":
                q = " or ".join([BeArkimet.__decode_timerange(i) for i in values])
            else:
                log.warning("Invalid filter: {}", k)
                continue
            matchers.append(k + ":" + q)
        return "" if not matchers else "; ".join(matchers)

    @staticmethod
    def get_datasets_format(datasets):
        """
        :return: format of files in datasets
        """

        formats = []
        cfg = arki.cfg.Sections.parse(BeArkimet.arkimet_conf)
        for ds in datasets:
            ds_section = cfg.section(ds)
            for k, v in ds_section.items():
                if k == "format":
                    formats.append(v)

        # check if all the datasets are of the same type (else return an error)
        # return the general format of the datasets (bufr or grib)
        if all(x == formats[0] for x in formats):
            return formats[0]
        else:
            return None

    @staticmethod
    def get_datasets_category(datasets):
        """
        :return: datasets category (forecast or observed)
        """
        category = []
        cfg = arki.cfg.Sections.parse(BeArkimet.arkimet_conf)
        for ds in datasets:
            ds_section = cfg.section(ds)
            for k, v in ds_section.items():
                if k == "_category":
                    category.append(v)
        # check if all the datasets are of the same type (else return an error)
        # return the general format of the datasets (bufr or grib)
        if all(x == category[0] for x in category):
            return category[0]
        else:
            return None

    # to configure observed datasets one by one
    @staticmethod
    def get_observed_dataset_params(dataset):
        cfg = arki.cfg.Sections.parse(BeArkimet.arkimet_conf)
        ds_section = cfg.section(dataset)
        filters = ""
        for k, v in ds_section.items():
            if k == "filter":
                filters = v

        filters_split = shlex.split(filters)
        # networks is the parameter that defines the different dataset for observed data
        networks = []
        for f in filters_split:
            if f.startswith("BUFR"):
                networks.append(f.split("=")[1])
        return networks

    # to configure all observed datasets at one time
    # @staticmethod
    # def get_observed_dataset_params(datasets):
    #     dataset_items = []
    #     cfg = arki.cfg.Sections.parse(BeArkimet.arkimet_conf)
    #     for ds in datasets:
    #         ds_params = {}
    #         filters = None
    #         ds_section = cfg.section(ds)
    #         for k, v in ds_section.items():
    #             if k == 'filter':
    #                 filters = v
    #         filters_split = shlex.split(filters)
    #         # networks is the parameter that defines the different dataset for observed data
    #         networks = []
    #         for f in filters_split:
    #             if f.startswith('BUFR'):
    #                 networks.append(f.split('=')[1])
    #         ds_params['dataset'] = ds
    #         ds_params['filters'] = networks
    #         dataset_items.append(ds_params)
    #     return dataset_items

    @staticmethod
    def from_network_to_dataset(network):
        cfg_sections = Sections()
        cfg = cfg_sections.parse(BeArkimet.arkimet_conf)
        for i in [a for a in cfg.items() if a[0] not in ["error", "duplicates"]]:
            filter = i[1]["filter"]
            filters_split = shlex.split(filter)
            # networks is the parameter that defines the different dataset for observed data
            nets = []
            for f in filters_split:
                if f.startswith("BUFR"):
                    nets.append(f.split("=")[1])
            if network in nets:
                return i[0]
        return None

    @staticmethod
    def from_dataset_to_networks(dataset):
        nets = []
        cfg_sections = Sections()
        cfg = cfg_sections.parse(BeArkimet.arkimet_conf)
        for i in [a for a in cfg.items() if a[0] == dataset]:
            filter = i[1]["filter"]
            filters_split = shlex.split(filter)
            # networks is the parameter that defines the different dataset for observed data
            for f in filters_split:
                if f.startswith("BUFR"):
                    nets.append(f.split("=")[1])
        return nets

    @staticmethod
    def get_obs_datasets(query, license):
        # actually this function is used only in tests and in a "side" script. For other purpose is better to use SqlApiDbManager.get_datasets that retrieve datasets from the db instead of arkimet config
        datasets = []
        cfg_sections = Sections()
        cfg = cfg_sections.parse(BeArkimet.arkimet_conf)
        for i in [a for a in cfg.items() if a[0] not in ["error", "duplicates"]]:
            category = i[1]["_category"]
            # check if the dataset is for observed data
            if category != "OBS":
                if i[0] != "multim-forecast":
                    continue
            # if a license is queried, filter by license
            if license:
                matches = False
                for lic in license:
                    if i[1]["_license"] != lic:
                        continue
                    else:
                        matches = True
                        break
                if not matches:
                    continue
            # filter by query
            if query:
                source = arki.dataset.Session().dataset_reader(cfg=i[1])
                summary = source.query_summary(query)
                if summary.count == 0:
                    continue
            # append the filtered datasets
            datasets.append(i[0])

            # if networks:
            #     # TODO choose if the network will be a single or multiple param
            #     filter = i[1]['filter']
            #     filters_split = shlex.split(filter)
            #     # networks is the parameter that defines the different dataset for observed data
            #     nets = []
            #     for f in filters_split:
            #         if f.startswith('BUFR'):
            #             nets.append(f.split('=')[1])
            #     if networks in nets:
            #         # append the id in dataset list
            #         datasets.append(i[0])
            #     continue
        return datasets

    @staticmethod
    def arkimet_extraction(datasets, query, outfile):
        cfg = arki.cfg.Sections.parse(BeArkimet.arkimet_conf)

        with open(outfile, mode="a+b") as outfile:
            for d in datasets:
                dt_part = cfg.section(d)
                source = arki.dataset.Session().dataset_reader(cfg=dt_part)
                bin_data = source.query_bytes(query, with_data=True)
                outfile.write(bin_data)

    @staticmethod
    def __decode_area(i):
        if not isinstance(i, dict):
            raise ValueError(f"Unexpected input type for <{type(i).__name__}>")
        style = i.get("style")
        # the notation is the old one: convert the name of the keys to the new notation
        if not style:
            style = i.get("s")
            i["value"] = i.get("va", {})
        vals = [k[0] + "=" + str(k[1]) for k in i.get("value", {}).items()]
        if style == "GRIB":
            return "GRIB:" + ",".join(vals) if vals else ""
        elif style == "ODIMH5":
            return "ODIMH5:" + ",".join(vals) if vals else ""
        elif style == "VM2":
            a = "VM2," + str(i.get(id))
            if vals:
                a = a + ":" + ",".join(vals)
            return a
        else:
            raise ValueError(f"Invalid <area> style for {style}")

    @staticmethod
    def __decode_level(i):
        if not isinstance(i, dict):
            raise TypeError(f"Unexpected input type for <{type(i).__name__}>")
        style = i.get("style")
        # the notation is the old one: convert the name of the keys to the new notation
        if not style:
            style = i.get("s")
            i["level_type"] = i.get("lt", "")
            i["scale"] = i.get("sc", "")
            i["value"] = i.get("va", "")
        if style == "GRIB1":
            lev = [str(i.get("level_type", ""))]
            l1 = str(i.get("l1", ""))
            if l1:
                lev.append(l1)
                l2 = str(i.get("l2", ""))
                if l2:
                    lev.append(l2)
            return "GRIB1," + ",".join(lev)
        elif style == "GRIB2S":
            lev = [str(i.get("level_type", "-")), "-", "-"]
            sc = str(i.get("scale", ""))
            if sc:
                lev[1] = sc
            va = str(i.get("value", ""))
            if va:
                lev[2] = va
            return "GRIB2S," + ",".join(lev)
        elif style == "GRIB2D":
            return "GRIB2D,{l1},{s1},{v1},{l2},{s2},{v2}".format(
                l1=i.get("l1", ""),
                s1=i.get("s1", ""),
                v1=i.get("v1", ""),
                l2=i.get("l2", ""),
                s2=i.get("s2", ""),
                v2=i.get("v2", ""),
            )
        elif style == "ODIMH5":
            return "ODIMH5,range {mi} {ma}".format(
                mi=i.get("mi", ""), ma=i.get("ma", "")
            )
        else:
            raise ValueError(f"Invalid <level> style for {style}")

    @staticmethod
    def __decode_origin(i):
        if not isinstance(i, dict):
            raise TypeError(f"Unexpected input type for <{type(i).__name__}>")
        style = i.get("style")
        # the notation is the old one: convert the name of the keys to the new notation
        if not style:
            style = i.get("s")
            i["centre"] = i.get("ce", "")
            i["subcentre"] = i.get("sc", "")
            i["process"] = i.get("pr", "")
            i["process_type"] = (i.get("pt", ""),)
            i["background_process_id"] = (i.get("bi", ""),)
            i["process_id"] = (i.get("pi", ""),)
        if style == "GRIB1":
            return "GRIB1,{ce},{sc},{pr}".format(
                ce=i.get("centre", ""),
                sc=i.get("subcentre", ""),
                pr=i.get("process", ""),
            )
        elif style == "GRIB2":
            return "GRIB2,{ce},{sc},{pt},{bi},{pi}".format(
                ce=i.get("centre", ""),
                sc=i.get("subcentre", ""),
                pt=i.get("process_type", ""),
                bi=i.get("background_process_id", ""),
                pi=i.get("process_id", ""),
            )
        elif style == "BUFR":
            return "BUFR,{ce},{sc}".format(ce=i.get("ce", ""), sc=i.get("sc", ""))
        elif style == "ODIMH5":
            return "ODIMH5,{wmo},{rad},{plc}".format(
                wmo=i.get("wmo", ""), rad=i.get("rad", ""), plc=i.get("plc", "")
            )
        else:
            raise ValueError(f"Invalid <origin> style for {style}")

    @staticmethod
    def __decode_proddef(i):
        if not isinstance(i, dict):
            raise TypeError(f"Unexpected input type for <{type(i).__name__}>")
        style = i.get("style")
        # the notation is the old one: convert the name of the keys to the new notation
        if not style:
            style = i.get("s")
            i["value"] = i.get("va", {})
        if style == "GRIB":
            vals = [k[0] + "=" + str(k[1]) for k in i.get("value", {}).items()]
            return "GRIB:" + ",".join(vals) if vals else ""
        else:
            raise ValueError(f"Invalid <proddef> style for {style}")

    @staticmethod
    def __decode_product(i):
        if not isinstance(i, dict):
            raise TypeError(f"Unexpected input type for <{type(i).__name__}>")
        style = i.get("style")
        # the notation is the old one: convert the name of the keys to the new notation
        if not style:
            style = i.get("s")
            i["origin"] = i.get("or", "")
            i["table"] = i.get("ta", "")
            i["product"] = i.get("pr", "")
            i["centre"] = i.get("ce", "")
            i["discipline"] = i.get("di", "")
            i["category"] = i.get("ca", "")
            i["number"] = i.get("no", "")
        if style == "GRIB1":
            return "GRIB1,{origin},{table},{product}".format(
                origin=i.get("origin", ""),
                table=i.get("table", ""),
                product=i.get("product", ""),
            )
        elif style == "GRIB2":
            return "GRIB2,{centre},{discipline},{category},{number}".format(
                centre=i.get("centre", ""),
                discipline=i.get("discipline", ""),
                category=i.get("category", ""),
                number=i.get("number", ""),
            )
        elif style == "BUFR":
            s = "BUFR,{ty},{st},{ls}".format(
                ty=i.get("ty", ""), st=i.get("st", ""), ls=i.get("ls", "")
            )
            vals = [k[0] + "=" + str(k[1]) for k in i.get("va", {}).items()]
            return "{}:{}".format(s, ",".join(vals)) if vals else s
        elif style == "ODIMH5":
            return "ODIMH5,{obj},{product}".format(
                obj=i.get("ob", ""), product=i.get("pr", "")
            )
        elif style == "VM2":
            p = "VM2,{id}".format(id=i.get("id", ""))
            vals = [k[0] + "=" + str(k[1]) for k in i.get("va", {}).items()]
            return "{}:{}".format(p, ",".join(vals)) if vals else p
        else:
            raise ValueError(f"Invalid <product> style for {style}")

    @staticmethod
    def __decode_quantity(i):
        if not isinstance(i, dict):
            raise TypeError(f"Unexpected input type for <{type(i).__name__}>")
        # check if the notation is the old one or the new one
        if "value" not in i.keys():
            i["value"] = i.get("va", [])
        return ",".join([str(k) for k in i.get("value", [])])

    @staticmethod
    def decode_run(i):
        if not isinstance(i, dict):
            raise TypeError(f"Unexpected input type for <{type(i).__name__}>")
        style = i.get("style")
        # the notation is the old one: convert the name of the keys to the new notation
        if not style:
            style = i.get("s")
            i["value"] = i.get("va", None)
        if style == "MINUTE":
            val = i.get("value")
            if not isinstance(val, int):
                raise TypeError("Run value must be a number")
            h = str(math.floor(val / 60)).zfill(2)
            m = str(val % 60).zfill(2)
            return f"MINUTE,{h}:{m}"
        else:
            raise ValueError(f"Invalid <run> style for {style}")

    @staticmethod
    def __decode_task(i):
        if not isinstance(i, dict):
            raise TypeError(f"Unexpected input type for <{type(i).__name__}>")
        # check if the notation is the old one or the new one
        if "value" not in i.keys():
            i["value"] = i.get("va", "")
        return str(i.get("value", ""))

    @staticmethod
    def __decode_timerange(i):
        if not isinstance(i, dict):
            raise TypeError(f"Unexpected input type for <{type(i).__name__}>")
        style = i.get("style")
        # the notation is the old one: convert the name of the keys to the new notation
        if not style:
            style = i.get("s")
            i["type"] = i.get("ty", "")
            i["unit"] = i.get("un", "")
            i["step_unit"] = i.get("su", -1)
            i["step_len"] = i.get("sl", -1)
        # un = {}
        if style == "GRIB1":
            un = {
                -1: "n/a",
                0: "m",
                1: "h",
                2: "d",
                3: "mo",
                4: "y",
                5: "de",
                6: "no",
                7: "ce",
                10: "h3",
                11: "h6",
                12: "h12",
                254: "s",
            }
            return "GRIB1,{type},{p1}{un},{p2}{un}".format(
                type=i.get("type", -1),
                p1=i.get("p1", -1),
                p2=i.get("p2", -1),
                un=un[i.get("unit", -1)],
            )
        elif style == "GRIB2":
            un = {
                -1: "n/a",
                0: "m",
                1: "h",
                2: "d",
                3: "mo",
                4: "y",
                5: "de",
                6: "no",
                7: "ce",
                10: "h3",
                11: "h6",
                12: "h12",
                254: "s",
            }
            return "GRIB2,{type},{p1}{un},{p2}{un}".format(
                type=i.get("type", -1),
                p1=i.get("p1", -1),
                p2=i.get("p2", -1),
                un=un[i.get("unit", -1)],
            )
        elif style == "Timedef":
            un = {
                -1: "n/a",
                0: "m",
                1: "h",
                2: "d",
                3: "mo",
                4: "y",
                5: "de",
                6: "no",
                7: "ce",
                10: "h3",
                11: "h6",
                12: "h12",
                13: "s",
            }
            s = "Timedef"
            if i.get("step_unit", -1) == 255:
                s = "".join([s, ",-"])
            else:
                s = "".join(
                    [s, ",{}{}".format(i.get("step_len"), un[i.get("step_unit", -1)])]
                )
            if i.get("pt"):
                s = "".join([s, ",{}".format(i.get("pt"))])
            else:
                """
                If i.pt is not defined, then the stat type is 255 and i.pl, i.pu are not defined too
                (see arki / types / timerange.cc:1358).
                If the stat type is 255, then proctype = "-"
                (see arki / types / timerange.cc:1403).
                """
                s = "".join([s, ",-"])

            """
            If i.pu is not defined, then the stat unit is UNIT_MISSING = 255 and i.pl is not defined too
            (see arki / types / timerange.cc:1361).
            If stat unit is 255, then proclen = "-"
            (see arki / types / timerange.cc:1408).
            """
            if i.get("pu", -1):
                s = "".join([s, ",{}{}".format(i.get("pl"), un[i.get("su", -1)])])
            else:
                s = "".join([s, ",-"])
            return s
        elif style == "BUFR":
            un = {
                -1: "n/a",
                0: "m",
                1: "h",
                2: "d",
                3: "mo",
                4: "y",
                5: "de",
                6: "no",
                7: "ce",
                10: "h3",
                11: "h6",
                12: "h12",
                13: "s",
            }
            return "BUFR,{val}{un}".format(val=i.get("va", -1), un=un[i.get("un", -1)])
        else:
            raise ValueError(f"Invalid <timerange> style for {style}")
