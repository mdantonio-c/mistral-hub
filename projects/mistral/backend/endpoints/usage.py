import os
import subprocess

from mistral.endpoints import DOWNLOAD_DIR
from restapi import decorators
from restapi.rest.definition import EndpointResource
from restapi.utilities.htmlcodes import hcodes


class Usage(EndpointResource):

    labels = ["usage"]

    @decorators.auth.require()
    @decorators.endpoint(
        path="/usage",
        summary="Get user disk usage.",
        responses={200: "Disk usage information"},
    )
    # 200: {'schema': {'$ref': '#/definitions/StorageUsage'}}
    def get(self):
        """
        Get actual user disk quota and current usage
        :return:
        """
        user = self.get_user()

        # get user disk quota
        # db = self.get_service_instance('sqlalchemy')
        # disk_quota = db.session.query(
        #     db.User.disk_quota).filter_by(id=user.id).scalar()
        # log.debug(disk_quota)

        # get current usage
        used_quota = 0
        user_dir = os.path.join(DOWNLOAD_DIR, user.uuid)
        if os.path.isdir(user_dir):
            used_quota = int(
                subprocess.check_output(["du", "-sb", user_dir]).split()[0]
            )

        data = {"quota": user.disk_quota, "used": used_quota}
        return self.response(data, code=hcodes.HTTP_OK_BASIC)
