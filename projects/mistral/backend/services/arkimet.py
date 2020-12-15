import json
import math
import os
import shlex
import subprocess

import arkimet as arki
import dateutil.parser
from arkimet.cfg import Sections
from mistral.exceptions import AccessToDatasetDenied, InvalidLicenseException
from restapi.utilities.logs import log

DATASET_ROOT = os.environ.get("DATASET_ROOT", "/")


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
    def get_unique_license(datasets):
        """
        Get license name for a give list of datasets.
        If the list of datasets does not share the same license, an exception is raised.
        Datasets that do not specify a license are not allowed.
        :return: the unique license name
        """
        if not datasets:
            raise ValueError("Unexpected empty datasets list")
        cfg_sections = Sections()
        cfg = cfg_sections.parse(BeArkimet.arkimet_conf)
        licenses = set()
        for ds in [a for a in cfg.items() if a[0] in datasets]:
            id_ = ds[0]
            val = ds[1].get("_license")
            if not val:
                raise InvalidLicenseException(f"Missing license for dataset {id_}")
            val = val.upper()
            if val not in BeArkimet.allowed_licenses:
                raise InvalidLicenseException(
                    "Unexpected license <{}> for dataset {}. "
                    "Allowed licenses are {}".format(
                        val, id_, list(BeArkimet.allowed_licenses)
                    )
                )
            licenses.add(val)
        return (
            list(licenses)[0]
            if len(licenses) == 1
            else InvalidLicenseException(
                f"Datasets do not share the same license. {licenses}"
            )
        )

    @staticmethod
    def check_compatible_licenses(db, datasets):
        """
        Check that the datasets belong to compatible licenses.
        :param db: database instance service
        :param datasets: list of datasets
        :return: shared license group
        """
        if not datasets:
            raise ValueError("Unexpected empty datasets list")
        cfg_sections = Sections()
        cfg = cfg_sections.parse(BeArkimet.arkimet_conf)
        groups_of_licenses = set()
        for ds in [a for a in cfg.items() if a[0] in datasets]:
            id = ds[0]
            license_name = ds[1].get("_license")
            if not license_name:
                raise InvalidLicenseException(f"Missing license for dataset {id}")
            # get the license group
            license_ = db.License.query.filter_by(name=license_name).first()
            group_license_id = license_.group_license_id
            gp_license = db.GroupLicense.query.filter_by(id=group_license_id).first()
            groups_of_licenses.add(gp_license)
        return (
            list(groups_of_licenses)[0]
            if len(groups_of_licenses) == 1
            else InvalidLicenseException(
                f"Datasets do not share the same license group. {groups_of_licenses}"
            )
        )

    @staticmethod
    def load_summary(datasets=[], query=""):
        """
        Get summary for one or more datasets. If no dataset is provided consider all available ones.
        :param datasets: List of datasets
        :param query: Optional arkimet query filter
        :return:
        """
        if not datasets:
            datasets = [d["id"] for d in BeArkimet.load_datasets()]
        if query is None:
            query = ""

        ds = " ".join([DATASET_ROOT + f"{i}" for i in datasets])
        args = shlex.split(
            f"arki-query --json --summary-short --annotate '{query}' {ds}"
        )
        log.debug("Launching Arkimet command: {}", args)

        proc = subprocess.Popen(args, encoding="utf-8", stdout=subprocess.PIPE)
        summary = json.loads(proc.stdout.read())
        if proc.wait() == 0:
            return summary
        else:
            raise AccessToDatasetDenied("Access to dataset denied")

        # with subprocess.Popen(args, encoding='utf-8', stdout=subprocess.PIPE) as proc:
        #     return json.loads(proc.stdout.read())

    @staticmethod
    def estimate_data_size(datasets, query):
        """
        Estimate arki-query output size.
        """
        cfg = arki.cfg.Sections.parse(BeArkimet.arkimet_conf)
        summary = arki.Summary()
        for d in datasets:
            dt = cfg.section(d)
            source = arki.dataset.Reader(dt)
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
    def get_obs_datasets(query, license):
        datasets = []
        cfg_sections = Sections()
        cfg = cfg_sections.parse(BeArkimet.arkimet_conf)
        for i in [a for a in cfg.items() if a[0] not in ["error", "duplicates"]]:
            category = i[1]["_category"]
            # check if the dataset is for observed data
            if category != "OBS":
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
                source = arki.dataset.Reader(i[1])
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
                source = arki.dataset.Reader(dt_part)
                bin_data = source.query_bytes(query, with_data=True)
                outfile.write(bin_data)

    @staticmethod
    def __decode_area(i):
        if not isinstance(i, dict):
            raise ValueError("Unexpected input type for <{}>".format(type(i).__name__))
        style = i.get("s")
        vals = [k[0] + "=" + str(k[1]) for k in i.get("va", {}).items()]
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
            raise TypeError("Unexpected input type for <{}>".format(type(i).__name__))
        style = i.get("s")
        if style == "GRIB1":
            lev = [str(i.get("lt", ""))]
            l1 = str(i.get("l1", ""))
            if l1:
                lev.append(l1)
                l2 = str(i.get("l2", ""))
                if l2:
                    lev.append(l2)
            return "GRIB1," + ",".join(lev)
        elif style == "GRIB2S":
            lev = [str(i.get("lt", "-")), "-", "-"]
            sc = str(i.get("sc", ""))
            if sc:
                lev[1] = sc
            va = str(i.get("va", ""))
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
            raise TypeError("Unexpected input type for <{}>".format(type(i).__name__))
        style = i.get("s")
        if style == "GRIB1":
            return "GRIB1,{ce},{sc},{pr}".format(
                ce=i.get("ce", ""), sc=i.get("sc", ""), pr=i.get("pr", "")
            )
        elif style == "GRIB2":
            return "GRIB2,{ce},{sc},{pt},{bi},{pi}".format(
                ce=i.get("ce", ""),
                sc=i.get("sc", ""),
                pt=i.get("pt", ""),
                bi=i.get("bi", ""),
                pi=i.get("pi", ""),
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
            raise TypeError("Unexpected input type for <{}>".format(type(i).__name__))
        style = i.get("s")
        if style == "GRIB":
            vals = [k[0] + "=" + str(k[1]) for k in i.get("va", {}).items()]
            return "GRIB:" + ",".join(vals) if vals else ""
        else:
            raise ValueError(f"Invalid <proddef> style for {style}")

    @staticmethod
    def __decode_product(i):
        if not isinstance(i, dict):
            raise TypeError("Unexpected input type for <{}>".format(type(i).__name__))
        style = i.get("s")
        if style == "GRIB1":
            return "GRIB1,{origin},{table},{product}".format(
                origin=i.get("or", ""), table=i.get("ta", ""), product=i.get("pr", "")
            )
        elif style == "GRIB2":
            return "GRIB2,{centre},{discipline},{category},{number}".format(
                centre=i.get("ce", ""),
                discipline=i.get("di", ""),
                category=i.get("ca", ""),
                number=i.get("no", ""),
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
            raise TypeError("Unexpected input type for <{}>".format(type(i).__name__))
        return ",".join([str(k) for k in i.get("va", [])])

    @staticmethod
    def decode_run(i):
        if not isinstance(i, dict):
            raise TypeError("Unexpected input type for <{}>".format(type(i).__name__))
        style = i.get("s")
        if style == "MINUTE":
            val = i.get("va")
            if not isinstance(val, int):
                raise TypeError("Run value must be a number")
            h = math.floor(i.get("va") / 60)
            m = val % 60
            if h < 10:
                h = "0" + str(h)
            if m < 10:
                m = "0" + str(m)
            return f"MINUTE,{h}:{m}"
        else:
            raise ValueError(f"Invalid <run> style for {style}")

    @staticmethod
    def __decode_task(i):
        if not isinstance(i, dict):
            raise TypeError("Unexpected input type for <{}>".format(type(i).__name__))
        return str(i.get("va", ""))

    @staticmethod
    def __decode_timerange(i):
        if not isinstance(i, dict):
            raise TypeError("Unexpected input type for <{}>".format(type(i).__name__))
        style = i.get("s")
        # un = {}
        if style == "GRIB1":
            un = {
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
                type=i.get("ty"), p1=i.get("p1"), p2=i.get("p2"), un=un[i.get("un")]
            )
        elif style == "GRIB2":
            un = {
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
                type=i.get("ty"), p1=i.get("p1"), p2=i.get("p2"), un=un[i.get("un")]
            )
        elif style == "Timedef":
            un = {
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
            if i.get("su") == 255:
                s = "".join([s, ",-"])
            else:
                s = "".join([s, ",{}{}".format(i.get("sl"), un[i.get("su")])])
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
            if i.get("pu"):
                s = "".join([s, ",{}{}".format(i.get("pl"), un[i.get("su")])])
            else:
                s = "".join([s, ",-"])
            return s
        elif style == "BUFR":
            un = {
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
            return "BUFR,{val}{un}".format(val=i.get("va"), un=un[i.get("un")])
        else:
            raise ValueError(f"Invalid <timerange> style for {style}")
