# -*- coding: utf-8 -*-


class CustomProfile(object):
    def __init__(self):
        pass

    def manipulate(self, ref, user, data):
        data['Disk Quota'] = user.disk_quota

        return data
