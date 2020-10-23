from mistral.services.arkimet import BeArkimet as arki
from restapi.customizer import BaseCustomizer
from restapi.models import AdvancedList, Schema, fields, validate
from restapi.utilities.logs import log


class Initializer:
    def __init__(self, services, app=None):

        sql = services["sqlalchemy"]

        admin = sql.Role.query.filter_by(name="admin_root").first()
        if admin is None:
            log.warning("Admin role does not exist")
        else:
            admin.description = "Administrator"
            sql.session.add(admin)

        user = sql.Role.query.filter_by(name="normal_user").first()
        if user is None:
            log.warning("User role does not exist")
        else:
            user.description = "User"

            sql.session.add(user)

        sql.session.commit()
        log.info("Roles successfully updated")

        # add license groups to db
        license_group_data_to_insert = [
            {"name": "CCBY_COMPLIANT", "descr": "Group of licenses CC BY compliant"},
            {
                "name": "CCBY-SA_COMPLIANT",
                "descr": "Group of licenses CC BY-SA compliant",
            },
        ]
        for el in license_group_data_to_insert:
            l_group = sql.GroupLicense.query.filter_by(name=el["name"]).first()
            if l_group is None:
                new_l_group = sql.GroupLicense(name=el["name"], descr=el["descr"])
                sql.session.add(new_l_group)
            else:
                # check if the element has to be updated
                if l_group.descr != el["descr"]:
                    l_group.descr = el["descr"]
                    sql.session.add(l_group)
        sql.session.commit()
        log.info("GroupLicense succesfully updated")

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
        log.info("Datasets successfully updated")

        celery = services["celery"]
        UNIQUE_NAME = "requests_cleanup"

        task = celery.get_periodic_task(name=UNIQUE_NAME)

        if task:
            log.info("Automatic_cleanup task already installed, deleting...")
            res = celery.delete_periodic_task(name=UNIQUE_NAME)
            log.info("Automatic_cleanup task deleted = {}", res)

        # EVERY = "5"
        # celery.create_periodic_task(
        #     name=UNIQUE_NAME,
        #     task="mistral.tasks.requests_cleanup.automatic_cleanup",
        #     every=EVERY,
        # )
        # log.info("Automa,tic_cleanup task installed every {} seconds", EVERY)
        HOUR = "3"
        MINUTE = "45"
        celery.create_crontab_task(
            name=UNIQUE_NAME,
            task="mistral.tasks.requests_cleanup.automatic_cleanup",
            hour=HOUR,
            minute=MINUTE,
            args=[],
        )

        log.info("Automatic_cleanup task installed every day at {}:{}", HOUR, MINUTE)


class GroupLicence(Schema):
    id = fields.Str()
    name = fields.Str()


class Datasets(Schema):
    id = fields.Str()
    name = fields.Str()


class Customizer(BaseCustomizer):
    @staticmethod
    def custom_user_properties_pre(properties):
        extra_properties = {}
        for p in ("datasets", "group_license"):
            if p in properties:
                extra_properties[p] = properties.pop(p, None)
        return properties, extra_properties

    @staticmethod
    def custom_user_properties_post(user, properties, extra_properties, db):

        licences = []
        for licence_id in extra_properties.get("group_license", []):
            lic = db.GroupLicense.query.filter_by(id=int(licence_id)).first()
            licences.append(lic)
        user.group_license = licences

        datasets = []
        for dataset_id in extra_properties.get("datasets", []):
            dat = db.GroupLicense.query.filter_by(id=int(dataset_id)).first()
            datasets.append(dat)
        user.datasets = datasets

    @staticmethod
    def manipulate_profile(ref, user, data):
        data["disk_quota"] = user.disk_quota
        data["amqp_queue"] = user.amqp_queue
        data["requests_expiration_days"] = user.requests_expiration_days
        data["datasets"] = user.datasets
        data["group_license"] = user.group_license

        return data

    @staticmethod
    def get_user_editable_fields(request):
        fields = Customizer.get_custom_input_fields(request)

        f = "requests_expiration_days"
        return {f: fields[f]}

    @staticmethod
    def get_custom_input_fields(request):

        # prevent queries at server startup
        if request:
            # Do not import it outside this function
            from restapi.services.detect import detector

            db = detector.get_service_instance("sqlalchemy")
            datasets = db.Datasets.query.all()
            licences = db.GroupLicense.query.all()
        else:
            datasets = []
            licences = []

        required = request and request.method == "POST"

        return {
            "disk_quota": fields.Int(
                required=required,
                # validate=validate.Range(min=0, max=???),
                validate=validate.Range(min=0),
                label="Disk quota",
                description="Disk quota in bytes",
            ),
            "amqp_queue": fields.Str(
                required=False,
                label="AMQP queue",
                description="AMQP queue used to notify the user",
            ),
            "requests_expiration_days": fields.Int(
                required=False,
                missing=0,
                validate=validate.Range(min=0, max=365),
                label="Requests expirations (in days, 0 to disable)",
                description="Number of days after which requests will be cleaned",
            ),
            "group_license": AdvancedList(
                fields.Str(
                    validate=validate.OneOf(
                        choices=[str(v.id) for v in licences],
                        labels=[v.name for v in licences],
                    )
                ),
                required=False,
                label="Allowed licences",
                description="",
                unique=True,
                multiple=True,
            ),
            "datasets": AdvancedList(
                fields.Str(
                    validate=validate.OneOf(
                        choices=[str(v.id) for v in datasets],
                        labels=[v.name for v in datasets],
                    )
                ),
                required=False,
                label="Allowed datasets",
                description="",
                unique=True,
                multiple=True,
            ),
        }

    @staticmethod
    def get_custom_output_fields(request):
        custom_fields = Customizer.get_custom_input_fields(request)

        custom_fields["datasets"] = fields.Nested(Datasets(many=True))
        custom_fields["group_license"] = fields.Nested(GroupLicence(many=True))

        return custom_fields
