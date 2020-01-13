# -*- coding: utf-8 -*-

""" CUSTOM Models for the relational database """

from restapi.models.sqlalchemy import db, User
from datetime import datetime

import enum

# Add (inject) attributes to User
setattr(User, 'my_custom_field', db.Column(db.String(255)))
setattr(User, 'disk_quota', db.Column(db.BigInteger, default=1073741824))   # 1 GB

setattr(User, 'requests', db.relationship('Request', backref='author', lazy='dynamic'))
setattr(User, 'fileoutput', db.relationship('FileOutput', backref='owner', lazy='dynamic'))
setattr(User, 'schedules', db.relationship('Schedule', backref='author', lazy='dynamic'))


class Request(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    name = db.Column(db.String, index=True, nullable=False)
    args = db.Column(db.String, nullable=False)
    submission_date = db.Column(db.DateTime, default=datetime.utcnow)
    end_date = db.Column(db.DateTime)
    status = db.Column(db.String(64))
    task_id = db.Column(db.String(64), index=True, unique=True)
    error_message = db.Column(db.Text)
    schedule_id = db.Column(db.Integer, db.ForeignKey('schedule.id'))
    fileoutput = db.relationship("FileOutput", backref='request', cascade="delete", uselist=False)

    def __repr__(self):
        return "<Request(name='{}', submission date='{}', status='{}')".format(
            self.name, self.submission_date, self.status)


class FileOutput(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(64), index=True, unique=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    size = db.Column(db.BigInteger)
    request_id = db.Column(db.Integer, db.ForeignKey('request.id'))

    def __repr__(self):
        return "<FileOutput(filename='{}', size='{}')".format(
            self.filename, self.size)


class PeriodEnum(enum.Enum):
    days = 1
    hours = 2
    minutes = 3
    seconds = 4
    microseconds = 5


class Schedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    submission_date = db.Column(db.DateTime, default=datetime.utcnow)
    name = db.Column(db.String, index=True, nullable=False)
    args = db.Column(db.String)
    is_crontab = db.Column(db.Boolean)
    period = db.Column(db.Enum(PeriodEnum))
    every = db.Column(db.Integer)
    crontab_settings = db.Column(db.String(64))
    on_data_ready = db.Column(db.Boolean, default=False)
    is_enabled = db.Column(db.Boolean)
    submitted_request = db.relationship('Request', backref='schedule', lazy='dynamic')

    def __repr__(self):
        return "<Schedule(name='{}', creation date='{}', enabled='{}')".format(
            self.name, self.submission_date, self.is_enabled)
