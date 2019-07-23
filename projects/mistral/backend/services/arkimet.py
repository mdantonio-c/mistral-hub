# -*- coding: utf-8 -*-

import shlex
import subprocess
import os
import glob
import re
import json
from utilities.logs import get_logger

DATASET_ROOT = os.environ.get('DATASET_ROOT', '/')
logger = get_logger(__name__)


class BeArkimet():

    @staticmethod
    def load_datasets():
        """
        Load dataset using arki-mergeconf
        $ arki-mergeconf $HOME/datasets/*

        :return: list of datasets
        """
        datasets = []
        folders = glob.glob(DATASET_ROOT + "*")
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

    @staticmethod
    def load_summary(datasets=[], query=''):
        """
        Get summary for one or more datasets. If no dataset is provided consider all available ones.
        :param datasets: List of datasets
        :param query: Optional arkimet query filter
        :return:
        """
        if not datasets:
            datasets = [d['id'] for d in BeArkimet.load_datasets()]
        if query is None:
            query = ''

        ds = ' '.join([DATASET_ROOT + '{}'.format(i) for i in datasets])
        args = shlex.split("arki-query --json --summary-short --annotate '{}' {}".format(query, ds))
        with subprocess.Popen(args, stdout=subprocess.PIPE) as proc:
            return json.loads(proc.stdout.read())

    @staticmethod
    def estimate_data_size(datasets, query):
        """
        Estimate arki-query output size.
        """
        ds = ' '.join([DATASET_ROOT + '{}'.format(i) for i in datasets])
        arki_summary_cmd = "arki-query --dump --summary-short '{}' {}".format(query, ds)
        args = shlex.split(arki_summary_cmd)
        p = subprocess.Popen(args, stdout=subprocess.PIPE)
        # extract the size
        return int(subprocess.check_output(('awk', '/Size/ {print $2}'), stdin=p.stdout))

    @staticmethod
    def parse_matchers(filters):
        matchers = []
        for k in filters:
            val = filters[k].strip()
            if k == 'origin':
                # -- GRIB1
                # -- Syntax: origin:GRIB1,centre,subcentre,process
                # -- Any of centre, subcentre, process can be omitted; if omitted, any value
                # -- will match
                if val.startswith('GRIB1') and re.match('GRIB1,?[0-9]*', val):
                    logger.debug('add <origin> matcher: {}'.format(val))
                    matchers.append('origin:'+val)
                else:
                    logger.warn('Invalid value for filter <origin>: %s' % val)
                    continue
            elif k == 'level':
                # -- GRIB1
                # -- Syntax: level:GRIB1, leveltype, l1, l2
                # -- Any of leveltype, l1 or l2 can be omitted; if omitted, any value
                # -- will match
                if val.startswith('GRIB1') and re.match('GRIB1,?[0-9]*', val):
                    matchers.append('level:'+val)
                else:
                    logger.warn('Invalid value for filter <level>: %s' % val)
                    continue
            # TODO manage the remaining filters

        return '' if not matchers else '; '.join(matchers)
