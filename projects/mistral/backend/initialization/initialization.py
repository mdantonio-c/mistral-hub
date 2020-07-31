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
                "name": "COSMO-LAMI",
                "descr": "COSMO-LAMI agreement between Italian Air Force Meteorological Service, Arpae Emilia-Romagna Idro-Meteo-Clima Service and Arpa Piemonte",
                "url": "",
            },
            {
                "name": "DPCN",
                "descr": "National Civil Protection Department-Presidency of the Council of Ministers",
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
                "url": "https://www.arpa.piemonte.it/chi-siamo/organizzazione/dipartimenti-tematici-arpa#naturali",
            },
            {
                "name": "ARPAL-APPP-CFR",
                "descr": "Lazio region - Arpal - Prevention planning and forecasting area - Regional functional center",
                "url": "http://www.regione.lazio.it/rl_protezione_civile/?vw=contenutiDettaglio&id=101",
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
                "url": "https://www.arpal.liguria.it",
            },
            {"name": "MISTRAL", "descr": "Mistral project", "url": ""},
            {
                "name": "R-MARCHE-PC",
                "descr": "Marche region – Civil Protection Service",
                "url": "https://www.regione.marche.it/Regione-Utile/Protezione-Civile",
            },
            {
                "name": "PROV-BOLZANO",
                "descr": "Meteorology and Avalanche Prevention Office - Civil Protection Agency - Autonomous Province of Bolzano",
                "url": "http://www.provincia.bz.it/it/contatti.asp?orga_orgaid=916",
            },
            {
                "name": "R-SARDEGNA-ARPAS-METEO",
                "descr": "Sardegna region – Arpas - Meteoclimatic Department",
                "url": "http://www.sar.sardegna.it/",
            },
        ]
        for el in attribution_data_to_insert:
            attribution = sql.Attribution.query.filter_by(name=el["name"]).first()
            if attribution is None:
                new_attribution = sql.Attribution(
                    name=el["name"], descr=el["descr"], url=el["url"],
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


class Customizer:
    """
    This class is used to manipulate user information
    - custom_user_properties is executed just before user creation
                             use this to removed or manipulate input properties
                             before sending to the database
    - custom_post_handle_user_input is used just after user registration
                                    use this to perform setup operations,
                                    such as verify default settings
    """

    def custom_user_properties(self, properties):
        return properties

    def custom_post_handle_user_input(self, auth, user_node, properties):
        return True
