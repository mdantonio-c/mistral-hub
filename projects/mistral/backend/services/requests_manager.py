from utilities.logs import get_logger
import json

log = get_logger(__name__)

class RequestManager ():

    @staticmethod
    def create_request_table(db,user,filters,task_id):
        request = db.Request
        args = json.dumps(filters)
        r = request(user_uuid=user, args=args, task_id=task_id)
        db.session.add(r)
        db.session.commit()
        request_id = r.id

        return request_id