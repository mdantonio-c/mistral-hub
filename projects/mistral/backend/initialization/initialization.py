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
