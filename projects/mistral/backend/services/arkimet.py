# -*- coding: utf-8 -*-

import os
import shlex, subprocess
import glob
from utilities.logs import get_logger

DATASET_ROOT = '/arkimet/datasets/'

logger = get_logger(__name__)

class BeArkimet():

    @staticmethod
    def load_datasets():
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
            while True:
                line = proc.stdout.readline()
                if not line:
                    break
                line = line.decode().strip()
                if line == '':
                    continue;
                if line.startswith('['):
                    # new dataset config
                    if ds is not None and ds['id'] not in ('error', 'duplicates'):
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