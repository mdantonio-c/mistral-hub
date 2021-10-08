""" CUSTOM Models for the relational database """

import enum
from datetime import datetime

from restapi.connectors.sqlalchemy.models import User, db
from sqlalchemy.dialects.postgresql import JSONB

# Add (inject) attributes to User
setattr(User, "disk_quota", db.Column(db.BigInteger, default=1073741824))  # 1 GB

setattr(User, "requests", db.relationship("Request", backref="author", lazy="dynamic"))
setattr(
    User, "fileoutput", db.relationship("FileOutput", backref="owner", lazy="dynamic")
)
setattr(
    User, "schedules", db.relationship("Schedule", backref="author", lazy="dynamic")
)
setattr(User, "amqp_queue", db.Column(db.String(255), nullable=True))
# In days, 0 to disable.
# Used by requests autocleaning to determine old requests to be deleted
setattr(User, "requests_expiration_days", db.Column(db.Integer, default=0))
setattr(User, "requests_expiration_delete", db.Column(db.Boolean, default=False))
setattr(User, "open_dataset", db.Column(db.Boolean))
# user configuration
setattr(User, "max_templates", db.Column(db.Integer))
setattr(User, "max_output_size", db.Column(db.BigInteger))
setattr(User, "allowed_postprocessing", db.Column(db.Boolean, default=False))
setattr(User, "allowed_schedule", db.Column(db.Boolean, default=False))
setattr(User, "allowed_obs_archive", db.Column(db.Boolean, default=False))
setattr(User, "request_par_hour", db.Column(db.Integer))


class Request(db.Model):  # type: ignore
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    name = db.Column(db.String, index=True, nullable=False)
    args = db.Column(JSONB, nullable=False)
    submission_date = db.Column(db.DateTime, default=datetime.utcnow)
    end_date = db.Column(db.DateTime)
    status = db.Column(db.String(64))
    task_id = db.Column(db.String(64), index=True, unique=True)
    error_message = db.Column(db.Text)
    schedule_id = db.Column(db.Integer, db.ForeignKey("schedule.id"))
    fileoutput = db.relationship(
        "FileOutput", backref="request", cascade="delete", uselist=False
    )
    opendata = db.Column(db.Boolean, default=False)
    archived = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return "<Request(name='{}', submission date='{}', status='{}')".format(
            self.name, self.submission_date, self.status
        )


class FileOutput(db.Model):  # type: ignore
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(64), index=True, unique=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    size = db.Column(db.BigInteger)
    request_id = db.Column(db.Integer, db.ForeignKey("request.id"))

    def __repr__(self):
        return f"<FileOutput(filename='{self.filename}', size='{self.size}')"


class PeriodEnum(enum.Enum):
    days = 1
    hours = 2
    minutes = 3
    seconds = 4
    microseconds = 5


class Schedule(db.Model):  # type: ignore
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    submission_date = db.Column(db.DateTime, default=datetime.utcnow)
    name = db.Column(db.String, index=True, nullable=False)
    args = db.Column(JSONB)
    is_crontab = db.Column(db.Boolean)
    period = db.Column(db.Enum(PeriodEnum))
    every = db.Column(db.Integer)
    crontab_settings = db.Column(db.String(64))
    on_data_ready = db.Column(db.Boolean, default=False)
    time_delta = db.Column(db.Interval)
    is_enabled = db.Column(db.Boolean)
    submitted_request = db.relationship("Request", backref="schedule", lazy="dynamic")
    opendata = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return "<Schedule(name='{}', creation date='{}', enabled='{}')".format(
            self.name, self.submission_date, self.is_enabled
        )


class GroupLicense(db.Model):  # type: ignore
    __tablename__ = "group_license"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, index=True, nullable=False)
    descr = db.Column(db.String, nullable=False)
    license = db.relationship("License", backref="group_license", lazy="dynamic")
    is_public = db.Column(db.Boolean)
    dballe_dsn = db.Column(db.String(64))


class License(db.Model):  # type: ignore
    __tablename__ = "license"
    id = db.Column(db.Integer, primary_key=True)
    group_license_id = db.Column(db.Integer, db.ForeignKey("group_license.id"))
    name = db.Column(db.String, index=True, nullable=False)
    descr = db.Column(db.String, nullable=False)
    url = db.Column(db.String)
    datasets = db.relationship("Datasets", backref="dataset_license", lazy="dynamic")


class Attribution(db.Model):  # type: ignore
    __tablename__ = "attribution"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, index=True, nullable=False)
    descr = db.Column(db.String, nullable=False)
    url = db.Column(db.String)
    datasets = db.relationship(
        "Datasets", backref="dataset_attribution", lazy="dynamic"
    )


class DatasetCategories(enum.Enum):
    FOR = 1
    OBS = 2
    RAD = 3


dataset_user_association_table = db.Table(
    "auth_association",
    db.Column("dataset_id", db.Integer, db.ForeignKey("datasets.id")),
    db.Column("user_id", db.Integer, db.ForeignKey("user.id")),
)


class Datasets(db.Model):  # type: ignore
    id = db.Column(db.Integer, primary_key=True)
    arkimet_id = db.Column(db.String, index=True, unique=True)
    name = db.Column(db.String, index=True, nullable=False, unique=True)
    description = db.Column(db.String, nullable=False)
    license_id = db.Column(db.Integer, db.ForeignKey("license.id"))
    attribution_id = db.Column(db.Integer, db.ForeignKey("attribution.id"))
    category = db.Column(db.Enum(DatasetCategories))
    fileformat = db.Column(db.String)
    bounding = db.Column(db.String)
    users = db.relationship(
        "User",
        secondary=dataset_user_association_table,
        backref="datasets",
        lazy="dynamic",
    )
