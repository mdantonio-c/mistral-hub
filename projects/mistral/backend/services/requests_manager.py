from utilities.logs import get_logger

logger = get_logger(__name__)

class RequestManager ():

    @staticmethod
    def create_request_table(db,user,filters):
        request = db.Request
        r = request(user_id=user, args=filters)
        db.session.add(r)
        #request_id = db.sess.query(request.id).

        for row in db.session.query(request).filter_by(user_id=user):
            request_id = (row.id)

        db.session.commit()
        return request_id