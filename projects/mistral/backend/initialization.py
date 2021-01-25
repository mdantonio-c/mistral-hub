from mistral.services.arkimet import BeArkimet as arki
from restapi.connectors import celery, sqlalchemy
from restapi.utilities.logs import log


class Initializer:
    def __init__(self, app=None):

        sql = sqlalchemy.get_instance()

        # add license groups to db
        license_group_data_to_insert = [
            {
                "name": "CCBY_COMPLIANT",
                "descr": "Group of licenses CC BY compliant",
                "is_public": True,
                "dballe_dsn": "DBALLE",
            },
            {
                "name": "CCBY-SA_COMPLIANT",
                "descr": "Group of licenses CC BY-SA compliant",
                "is_public": True,
                "dballe_dsn": None,
            },
        ]
        for el in license_group_data_to_insert:
            l_group = sql.GroupLicense.query.filter_by(name=el["name"]).first()
            if l_group is None:
                new_l_group = sql.GroupLicense(
                    name=el["name"],
                    descr=el["descr"],
                    is_public=el["is_public"],
                    dballe_dsn=el["dballe_dsn"],
                )
                sql.session.add(new_l_group)
            else:
                # check if the element has to be updated
                if (
                    l_group.descr != el["descr"]
                    or l_group.is_public != el["is_public"]
                    or l_group.dballe_dsn != el["dballe_dsn"]
                ):
                    l_group.is_public = el["is_public"]
                    l_group.descr = el["descr"]
                    l_group.dballe_dsn = el["dballe_dsn"]
                    sql.session.add(l_group)
        sql.session.commit()
        log.info("GroupLicense succesfully updated")

        l_groups_in_db = sql.GroupLicense.query.filter_by().all()
        for l_group_in_db in l_groups_in_db:
            is_in_script = False
            for l_group in license_group_data_to_insert:
                if l_group["name"] == l_group_in_db.name:
                    is_in_script = True
                    break
            if not is_in_script:
                log.warning(
                    "License group {} has an entry in db but is not in the inizializing schema",
                    l_group_in_db.name,
                )

        # add license to db
        license_data_to_insert = [
            {
                "group_name": "CCBY_COMPLIANT",
                "name": "CCBY4.0",
                "descr": "CC BY 4.0",
                "url": "https://creativecommons.org/licenses/by/4.0/legalcode",
            },
            {
                "group_name": "CCBY-SA_COMPLIANT",
                "name": "CCBY-SA4.0",
                "descr": "CC BY-SA 4.0",
                "url": "https://creativecommons.org/licenses/by-sa/4.0/",
            },
            {
                "group_name": "CCBY-SA_COMPLIANT",
                "name": "CCBY-NC-SA 3.0",
                "descr": "CC BY-NC-SA 3.0",
                "url": "https://creativecommons.org/licenses/by-nc-sa/3.0/",
            },
        ]

        for el in license_data_to_insert:
            lic = sql.License.query.filter_by(name=el["name"]).first()
            group_lic = sql.GroupLicense.query.filter_by(name=el["group_name"]).first()
            if group_lic is None:
                log.error(
                    "Licence {} cannot be updated: license group {} does not exists",
                    el["group_name"],
                    el["name"],
                )
                continue
            if lic is None:
                new_lic = sql.License(
                    name=el["name"],
                    descr=el["descr"],
                    group_license_id=group_lic.id,
                    url=el["url"],
                )
                sql.session.add(new_lic)
            else:
                # check if licence has to be updated
                if (
                    lic.group_license_id != group_lic.id
                    or lic.descr != el["descr"]
                    or lic.url != el["url"]
                ):
                    lic.group_license_id = group_lic.id
                    lic.descr = el["descr"]
                    lic.url = el["url"]
                    sql.session.add(lic)

        # add attribution to db
        attribution_data_to_insert = [
            {
                "name": "ARPAE-SIMC",
                "descr": "Arpae Emilia-Romagna Idro-Meteo-Clima Service",
                "url": "https://www.arpae.it/sim/",
            },
            {
                "name": "AM ARPAE ARPAP",
                "descr": "LAMI agreement between Italian Air Force Meteorological Service, Arpae Emilia-Romagna Idro-Meteo-Clima Service and Arpa Piemonte",
                "url": "",
            },
            {
                "name": "DPCN",
                "descr": "Department of Civil Protection - Presidency of the Council of Ministers",
                "url": "http://www.protezionecivile.gov.it",
            },
            {
                "name": "ECMWF-MISTRAL",
                "descr": "ECMWF - CEF european project - MISTRAL",
                "url": "",
            },
            {
                "name": "ARPAP-MISTRAL",
                "descr": "Arpa Piemonte - CEF european project - MISTRAL",
                "url": "",
            },
            {
                "name": "ARPAP-DRNA",
                "descr": "Arpa Piemonte - Department of Natural and Environmental Risks",
                "url": "http://www.arpa.piemonte.it/rischinaturali/",
            },
            {
                "name": "ARPAL-APPP-CFR",
                "descr": "Lazio region - Arpalazio - Prevention planning and forecasting area - Regional functional center",
                "url": "http://www.arpalazio.gov.it/",
            },
            {
                "name": "ARPACAMP-CFR",
                "descr": "Campania region - Regional functional center",
                "url": "http://centrofunzionale.regione.campania.it/#/pages/dashboard",
            },
            {
                "name": "ARPACAL-CFR",
                "descr": "Calabria region - Arpacal - Regional multi-risk functional center for local security",
                "url": "http://www.cfd.calabria.it",
            },
            {
                "name": "R-UMBRIA-SIR",
                "descr": "Umbria region -  Regional Hydrographic Service",
                "url": "http://servizioidrografico.regione.umbria.it/",
            },
            {
                "name": "R-LIGURIA-ARPAL",
                "descr": "Liguria region - Arpal",
                "url": "https://www.arpal.liguria.it/homepage/meteo.html",
            },
            {
                "name": "MISTRAL",
                "descr": "Mistral project",
                "url": "https://www.mistralportal.it",
            },
            {
                "name": "R-MARCHE-PC",
                "descr": "Marche region – Civil Protection Service",
                "url": "https://www.regione.marche.it/Regione-Utile/Protezione-Civile/Strutture-Operative/Centro-Funzionale-Multirischi",
            },
            {
                "name": "P-BOLZANO-PC",
                "descr": "Autonomous Province of Bolzano - Civil Protection Agency - Meteorology and Avalanche Prevention Office",
                "url": "https://appc.provincia.bz.it",
            },
            {
                "name": "ARPAS-METEO",
                "descr": "Sardinia Region - ARPAS - Meteoclimatic Department",
                "url": "http://www.sar.sardegna.it/",
            },
            {
                "name": "R-VENETO-ARPAV",
                "descr": "Veneto Region - ARPAV - Regional Agency for Environmental Protection",
                "url": "https://www.arpa.veneto.it/",
            },
            {
                "name": "R-SICILIA-ARPA",
                "descr": "Sicilia Region - ARPA Sicilia - Hydraulic and Hydrogeological Risk Service",
                "url": "https://www.arpa.sicilia.it/",
            },
            {
                "name": "P-TRENTO-SPR",
                "descr": "Autonomous Province of Trento - Prevention and Risks Service",
                "url": "https://dati.trentino.it/dataset/meteo-data",
            },
            {
                "name": "MeteoNetwork",
                "descr": "MeteoNetwork Association OdV",
                "url": "https://www.meteonetwork.it/",
            },
        ]
        for el in attribution_data_to_insert:
            attribution = sql.Attribution.query.filter_by(name=el["name"]).first()
            if attribution is None:
                new_attribution = sql.Attribution(
                    name=el["name"],
                    descr=el["descr"],
                    url=el["url"],
                )
                sql.session.add(new_attribution)
            else:
                # check if licence has to be updated
                if attribution.descr != el["descr"] or attribution.url != el["url"]:
                    attribution.descr = el["descr"]
                    attribution.url = el["url"]
                    sql.session.add(attribution)
        sql.session.commit()
        log.info("License and attributions successfully updated")

        license_in_db = sql.License.query.filter_by().all()
        for lic_in_db in license_in_db:
            is_in_script = False
            for lic in license_data_to_insert:
                if lic["name"] == lic_in_db.name:
                    is_in_script = True
                    break
            if not is_in_script:
                log.warning(
                    "License {} has an entry in db but is not in the inizializing schema",
                    lic_in_db.name,
                )

        attribution_in_db = sql.Attribution.query.filter_by().all()
        for attr_in_db in attribution_in_db:
            is_in_script = False
            for attr in attribution_data_to_insert:
                if attr["name"] == attr_in_db.name:
                    is_in_script = True
                    break
            if not is_in_script:
                log.warning(
                    "Attribution {} has an entry in db but is not in the inizializing schema",
                    attr_in_db.name,
                )

        # update dataset table
        datasets = arki.load_datasets()
        for ds in datasets:
            required_fields = [
                "id",
                "name",
                "description",
                "license",
                "attribution",
                "category",
            ]
            if not all(fields in ds for fields in required_fields):
                log.error("Config for dataset {} is not complete", ds["name"])
                continue
            ds_entry = sql.Datasets.query.filter_by(arkimet_id=ds["id"]).first()
            ds_attribution = sql.Attribution.query.filter_by(
                name=ds["attribution"]
            ).first()
            ds_license = sql.License.query.filter_by(name=ds["license"]).first()
            if ds_attribution is None:
                log.error(
                    "Dataset {} cannot be updated: attribution {} does not exist",
                    ds["name"],
                    ds["attribution"],
                )
                continue
            if ds_license is None:
                log.error(
                    "Dataset {} cannot be updated: license {} does not exist",
                    ds["name"],
                    ds["license"],
                )
                continue
            if ds_entry is None:
                new_ds = sql.Datasets(
                    arkimet_id=ds["id"],
                    name=ds["name"],
                    description=ds["description"],
                    license_id=ds_license.id,
                    attribution_id=ds_attribution.id,
                    category=ds["category"],
                )
                if "format" in ds:
                    new_ds.fileformat = ds["format"]
                if "bounding" in ds:
                    new_ds.bounding = ds["bounding"]
                sql.session.add(new_ds)
            else:
                # check if the dataset entry has to be updated
                if (
                    ds_entry.name != ds["name"]
                    or ds_entry.description != ds["description"]
                    or ds_entry.license_id != ds_license.id
                    or ds_entry.attribution_id != ds_attribution.id
                    or ds_entry.category != ds["category"]
                ):
                    ds_entry.name = ds["name"]
                    ds_entry.description = ds["description"]
                    ds_entry.license_id = ds_license.id
                    ds_entry.attribution_id = ds_attribution.id
                    ds_entry.category = ds["category"]
                    sql.session.add(ds_entry)
                if "format" in ds and ds_entry.fileformat != ds["format"]:
                    ds_entry.fileformat = ds["format"]
                if "bounding" in ds and ds_entry.bounding != ds["bounding"]:
                    ds_entry.bounding = ds["bounding"]
        sql.session.commit()
        dataset_in_db = sql.Datasets.query.filter_by().all()
        for ds_in_db in dataset_in_db:
            is_in_config = False
            for ds in datasets:
                if ds["name"] == ds_in_db.name:
                    is_in_config = True
                    break
            if not is_in_config:
                log.warning(
                    "Dataset {} has an entry in db but is not in the arkimet config",
                    ds_in_db.name,
                )

        log.info("Datasets successfully updated")

        celery_app = celery.get_instance()
        UNIQUE_NAME = "requests_cleanup"

        task = celery_app.get_periodic_task(name=UNIQUE_NAME)

        if task:
            log.info("Automatic_cleanup task already installed, deleting...")
            res = celery_app.delete_periodic_task(name=UNIQUE_NAME)
            log.info("Automatic_cleanup task deleted = {}", res)

        HOUR = "3"
        MINUTE = "45"
        celery_app.create_crontab_task(
            name=UNIQUE_NAME,
            # task="mistral.tasks.requests_cleanup.automatic_cleanup",
            task="automatic_cleanup",
            hour=HOUR,
            minute=MINUTE,
            args=[],
        )

        log.info("Automatic_cleanup task installed every day at {}:{}", HOUR, MINUTE)
