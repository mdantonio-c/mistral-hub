# -*- coding: utf-8 -*-

import os
import shlex, subprocess
import glob
from restapi.rest.definition import EndpointResource
from restapi.exceptions import RestApiException
from restapi.decorators import catch_error
from utilities import htmlcodes as hcodes
from utilities.logs import get_logger

logger = get_logger(__name__)


class Datasets(EndpointResource):

    @catch_error()
    def get(self, dataset_name=None):
        """ Get all the datasets or a specific one if a name is provided."""
        datasets = self._load_datasets()
        if dataset_name is not None:
            # retrieve dataset by name
            logger.debug("retrive datset by name '{}'".format(dataset_name))
            matched_ds = next((ds for ds in datasets if ds.get('id', '') == dataset_name), None)
            if not matched_ds:
                raise RestApiException(
                    "Dataset not found for name: {}".format(dataset_name),
                    status_code=hcodes.HTTP_BAD_NOTFOUND)
            return self.force_response(matched_ds)
        return self.force_response(datasets)

    def _load_datasets(self):
        '''
        Load dataset using arki-mergeconf
        $ arki-mergeconf $HOME/datasets/*

        :return: list of datasets
        '''
        datasets = []
        folders = glob.glob("/arkimet/datasets/*")
        args = shlex.split("arki-mergeconf " + ' '.join(folders))
        with subprocess.Popen(args, stdout=subprocess.PIPE) as proc:
            ds = None
            new_ds = False
            while True:
                line = proc.stdout.readline()
                if not line:
                    break
                line = line.decode().strip()
                if line == '':
                    continue;
                if line.startswith('['):
                    # new dataset config
                    if ds is not None and 'type' in ds:
                        datasets.append(ds)
                    ds = {
                        'id': line.split('[', 1)[1].split(']')[0]
                    }
                    continue;
                '''
                  name <str>
                  description <str>
                  allowed <bool>
                  bounding <str>
                  postprocess <list>
                '''
                name, val = line.partition("=")[::2]
                name = name.strip()
                val = val.strip()
                if name in ('name', 'description', 'bounding'):
                    ds[name] = val
                elif name == 'allowed':
                    ds[name] = bool(val)
                elif name == 'postprocess':
                    ds[name] = val.split(",")
            # add the latest ds
            datasets.append(ds)
        return datasets
