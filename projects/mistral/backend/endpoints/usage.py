import os
import subprocess

from mistral.endpoints import DOWNLOAD_DIR
from restapi import decorators
from restapi.rest.definition import EndpointResource, Response
from restapi.services.authentication import User


class Usage(EndpointResource):

    labels = ["usage"]

    @decorators.auth.require()
    @decorators.endpoint(
        path="/usage",
        summary="Get user disk usage.",
        responses={200: "Disk usage information"},
    )
    # 200: {'schema': {'$ref': '#/definitions/StorageUsage'}}
    def get(self, user: User) -> Response:
        """
        Get actual user disk quota and current usage
        """
        used_quota = 0
        user_dir = os.path.join(DOWNLOAD_DIR, user.uuid)
        if os.path.isdir(user_dir):
            used_quota = int(
                subprocess.check_output(["du", "-sb", user_dir]).split()[0]
            )

        data = {"quota": user.disk_quota, "used": used_quota}
        return self.response(data)
