from restapi.utilities.logs import log


class Initializer:
    def __init__(self, services, app=None):

        self.sql = services["sqlalchemy"]

        admin = self.sql.Role.query.filter_by(name="admin_root").first()
        if admin is None:
            log.warning("Admin role does not exist")
        else:
            admin.description = "Administrator"
            self.sql.session.add(admin)

        user = self.sql.Role.query.filter_by(name="normal_user").first()
        if user is None:
            log.warning("User role does not exist")
        else:
            user.description = "User"

            self.sql.session.add(user)

        self.sql.session.commit()
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
            l_group = self.sql.GroupLicense.query.filter_by(name=el["name"]).first()
            if l_group is None:
                new_l_group = self.sql.GroupLicense(name=el["name"], descr=el["descr"])
                self.sql.session.add(new_l_group)
        self.sql.session.commit()
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
        ]
        for el in license_data_to_insert:
            lic = self.sql.License.query.filter_by(name=el["name"]).first()
            if lic is None:
                group_lic = self.sql.GroupLicense.query.filter_by(
                    name=el["group_name"]
                ).first()
                if group_lic is None:
                    log.error(
                        "{} license group for {} license does not exists: License element cannot be updated",
                        el["group_name"],
                        el["name"],
                    )
                    continue
                new_lic = self.sql.License(
                    name=el["name"], descr=el["descr"], group_license_id=group_lic.id
                )
                if "url" in el:
                    new_lic.url = el["url"]
                self.sql.session.add(new_lic)

        # add attribution to db
        attribution_data_to_insert = [
            {
                "name": "ARPAE-SIMC",
                "descr": "Arpae Emilia Romagna Servizio Idro-Meteo-Clima",
                "url": "https://www.arpae.it/sim/",
            },
            {
                "name": "COSMO-LAMI",
                "descr": "Accordo COSMO-LAMI tra Servizio meteorologico dell´Aeronautica militare, Servizio IdroMeteoClima di Arpae Emilia-Romagna e di Arpa Piemonte",
            },
            {"name": "DPCN", "descr": "Dipartimento Protezione Civile Nazionale"},
            {
                "name": "ECMWF-MISTRAL",
                "descr": "ECMWF - Progetto europeo CEF - MISTRAL",
            },
            {
                "name": "ARPAP-MISTRAL",
                "descr": "Arpa Piemonte - Progetto europeo CEF - MISTRAL",
            },
            {
                "name": "ARPAP-DRNA",
                "descr": "Arpa Piemonte - Dipartimento Rischi Naturali e Ambientali",
            },
            {
                "name": "ARPAL-APPP-CFR",
                "descr": "Regione Lazio - Arpal - Area Prevenzione pianificazione e Previsione - Centro funzionale regionale",
            },
            {
                "name": "ARPACAMP-CFR",
                "descr": "Regione Campania - Centro funzionale regionale",
            },
            {
                "name": "ARPACAL-CFR",
                "descr": "Regione Calabria - Arpacal - Centro regionale  funzionale multirischi sicurezza sul territorio",
            },
            {
                "name": "R-UMBRIA-SIR",
                "descr": "Regione Umbria -  Servizio Idrografico Regionale",
                "url": "http://servizioidrografico.regione.umbria.it/",
            },
            {"name": "R-LIGURIA-ARPAL", "descr": "Regione Liguria - Arpal"},
            {"name": "MISTRAL", "descr": "Mistral project"},
        ]
        for el in attribution_data_to_insert:
            attribution = self.sql.Attribution.query.filter_by(name=el["name"]).first()
            if attribution is None:
                new_attribution = self.sql.Attribution(
                    name=el["name"], descr=el["descr"]
                )
                if "url" in el:
                    new_attribution.url = el["url"]
                self.sql.session.add(new_attribution)

        self.sql.session.commit()
        log.info("License and attributions successfully updated")


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
