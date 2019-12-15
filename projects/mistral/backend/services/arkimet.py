# -*- coding: utf-8 -*-

import shlex
import subprocess
import os
import glob
import json
import math
import dateutil
from restapi.utilities.logs import log

DATASET_ROOT = os.environ.get('DATASET_ROOT', '/')


class BeArkimet():

    allowed_filters = (
        'area', 'level', 'origin', 'proddef', 'product', 'quantity', 'run', 'task', 'timerange'
    )

    allowed_processors = (
        'additional_variables',
    )

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
        log.debug('Launching Arkimet command: {}', args)

        proc = subprocess.run(args, encoding='utf-8', stdout=subprocess.PIPE)
        log.debug('return code: {}', proc.returncode)
        # raise a CalledProcessError if returncode is non-zero
        proc.check_returncode()
        ds = None
        for line in proc.stdout.split('\n'):
            line = line.strip()
            if line == '':
                continue
            if line.startswith('['):
                # new dataset config
                if ds is not None and ds['id'] not in ('error', 'duplicates'):
                    datasets.append(ds)
                ds = {
                    'id': line.split('[', 1)[1].split(']')[0]
                }
                continue
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
        log.debug('Launching Arkimet command: {}', args)

        with subprocess.Popen(args, encoding='utf-8', stdout=subprocess.PIPE) as proc:
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
    def is_filter_allowed(filter_name):
        return True if filter_name in BeArkimet.allowed_filters else False

    @staticmethod
    def is_processor_allowed(processor_name):
        return True if processor_name in BeArkimet.allowed_processors else False

    @staticmethod
    def parse_reftime(from_str, to_str):
        """
        Return Arkimet reftime query
        :param from_str: ISO8610 date-time
        :type from_str: string
        :param to_str: ISO8610 date-time
        :type to_str: string
        :return: Arkimet query for reftime
        """
        from_dt = dateutil.parser.parse(from_str)
        to_dt = dateutil.parser.parse(to_str)

        gt = from_dt.strftime("%Y-%m-%d %H:%M")
        lt = to_dt.strftime("%Y-%m-%d %H:%M")
        return 'reftime: >={},<={}'.format(gt, lt)

    @staticmethod
    def parse_matchers(filters):
        """
        Parse incoming filters and return an arkimet query.
        :param filters:
        :return:
        """
        matchers = []
        for k in filters:
            values = filters[k]
            if not isinstance(values, list):
                values = [values]
            log.debug(values)
            if k == 'area':
                q = ' or '.join([BeArkimet.__decode_area(i) for i in values])
            elif k == 'level':
                q = ' or '.join([BeArkimet.__decode_level(i) for i in values])
            elif k == 'origin':
                q = ' or '.join([BeArkimet.__decode_origin(i) for i in values])
            elif k == 'proddef':
                q = ' or '.join([BeArkimet.__decode_proddef(i) for i in values])
            elif k == 'product':
                q = ' or '.join([BeArkimet.__decode_product(i) for i in values])
            elif k == 'quantity':
                q = ' or '.join([BeArkimet.__decode_quantity(i) for i in values])
            elif k == 'run':
                q = ' or '.join([BeArkimet.__decode_run(i) for i in values])
            elif k == 'task':
                q = ' or '.join([BeArkimet.__decode_task(i) for i in values])
            elif k == 'timerange':
                q = ' or '.join([BeArkimet.__decode_timerange(i) for i in values])
            else:
                log.warning('Invalid filter: {}', k)
                continue
            matchers.append(k + ':' + q)
        return '' if not matchers else '; '.join(matchers)

    @staticmethod
    def __decode_area(i):
        if not isinstance(i, dict):
            raise ValueError('Unexpected input type for <{}>'.format(type(i).__name__))
        style = i.get('s')
        vals = [k[0] + '=' + str(k[1]) for k in i.get('va', {}).items()]
        if style == 'GRIB':
            return 'GRIB:' + ','.join(vals) if vals else ''
        elif style == 'ODIMH5':
            return 'ODIMH5:' + ','.join(vals) if vals else ''
        elif style == 'VM2':
            a = 'VM2,' + str(i.get(id))
            if vals:
                a = a + ':' + ','.join(vals)
            return a
        else:
            raise ValueError('Invalid <area> style for {}'.format(style))

    @staticmethod
    def __decode_level(i):
        if not isinstance(i, dict):
            raise TypeError('Unexpected input type for <{}>'.format(type(i).__name__))
        style = i.get('s')
        if style == 'GRIB1':
            l = [str(i.get('lt', ''))]
            l1 = str(i.get('l1', ''))
            if l1:
                l.append(l1)
                l2 = str(i.get('l2', ''))
                if l2:
                    l.append(l2)
            return 'GRIB1,' + ','.join(l)
        elif style == 'GRIB2S':
            l = [str(i.get('lt', '-')), '-', '-']
            sc = str(i.get('sc', ''))
            if sc:
                l[1] = sc
            va = str(i.get('va', ''))
            if va:
                l[2] = va
            return 'GRIB2S,' + ','.join(l)
        elif style == 'GRIB2D':
            return 'GRIB2D,{l1},{s1},{v1},{l2},{s2},{v2}'.format(
                l1=i.get('l1', ''), s1=i.get('s1', ''), v1=i.get('v1', ''),
                l2=i.get('l2', ''), s2=i.get('s2', ''), v2=i.get('v2', '')
            )
        elif style == 'ODIMH5':
            return 'ODIMH5,range {mi} {ma}'.format(
                mi=i.get('mi', ''), ma=i.get('ma', '')
            )
        else:
            raise ValueError('Invalid <level> style for {}'.format(style))

    @staticmethod
    def __decode_origin(i):
        if not isinstance(i, dict):
            raise TypeError('Unexpected input type for <{}>'.format(type(i).__name__))
        style = i.get('s')
        if style == 'GRIB1':
            return 'GRIB1,{ce},{sc},{pr}'.format(
                ce=i.get('ce', ''),
                sc=i.get('sc', ''),
                pr=i.get('pr', '')
            )
        elif style == 'GRIB2':
            return 'GRIB2,{ce},{sc},{pt},{bi},{pi}'.format(
                ce=i.get('ce', ''),
                sc=i.get('sc', ''),
                pt=i.get('pt', ''),
                bi=i.get('bi', ''),
                pi=i.get('pi', '')
            )
        elif style == 'BUFR':
            return 'BUFR,{ce},{sc}'.format(
                ce=i.get('ce', ''),
                sc=i.get('sc', '')
            )
        elif style == 'ODIMH5':
            return 'ODIMH5,{wmo},{rad},{plc}'.format(
                wmo=i.get('wmo', ''),
                rad=i.get('rad', ''),
                plc=i.get('plc', '')
            )
        else:
            raise ValueError('Invalid <origin> style for {}'.format(style))

    @staticmethod
    def __decode_proddef(i):
        if not isinstance(i, dict):
            raise TypeError('Unexpected input type for <{}>'.format(type(i).__name__))
        style = i.get('s')
        if style == 'GRIB':
            vals = [k[0] + '=' + str(k[1]) for k in i.get('va', {}).items()]
            return 'GRIB:' + ','.join(vals) if vals else ''
        else:
            raise ValueError('Invalid <proddef> style for {}'.format(style))

    @staticmethod
    def __decode_product(i):
        if not isinstance(i, dict):
            raise TypeError('Unexpected input type for <{}>'.format(type(i).__name__))
        style = i.get('s')
        if style == 'GRIB1':
            return 'GRIB1,{origin},{table},{product}'.format(
                origin=i.get('or', ''),
                table=i.get('ta', ''),
                product=i.get('pr', '')
            )
        elif style == 'GRIB2':
            return 'GRIB2,{centre},{discipline},{category},{number}'.format(
                centre=i.get('ce', ''),
                discipline=i.get('di', ''),
                category=i.get('ca', ''),
                number=i.get('no', ''),
            )
        elif style == 'BUFR':
            s = 'BUFR,{ty},{st},{ls}'.format(
                ty=i.get('ty', ''),
                st=i.get('st', ''),
                ls=i.get('ls', '')
            )
            vals = [k[0] + '=' + str(k[1]) for k in i.get('va', {}).items()]
            return '{}:{}'.format(s, ','.join(vals)) if vals else s
        elif style == 'ODIMH5':
            return 'ODIMH5,{obj},{product}'.format(
                obj=i.get('ob', ''),
                product=i.get('pr', '')
            )
        elif style == 'VM2':
            p = 'VM2,{id}'.format(i.get('id', ''))
            vals = [k[0] + '=' + str(k[1]) for k in i.get('va', {}).items()]
            return '{}:{}'.format(p, ','.join(vals)) if vals else p
        else:
            raise ValueError('Invalid <product> style for {}'.format(style))

    @staticmethod
    def __decode_quantity(i):
        if not isinstance(i, dict):
            raise TypeError('Unexpected input type for <{}>'.format(type(i).__name__))
        return ','.join([str(k) for k in i.get('va', [])])

    @staticmethod
    def __decode_run(i):
        if not isinstance(i, dict):
            raise TypeError('Unexpected input type for <{}>'.format(type(i).__name__))
        style = i.get('s')
        if style == 'MINUTE':
            val = i.get('va')
            if not isinstance(val, int):
                raise TypeError('Run value must be a number')
            h = math.floor(i.get('va') / 60)
            m = val % 60
            if h < 10:
                h = '0' + str(h)
            if m < 10:
                m = '0' + str(m)
            return 'MINUTE,{hour}:{minute}'.format(hour=h, minute=m)
        else:
            raise ValueError('Invalid <run> style for {}'.format(style))

    @staticmethod
    def __decode_task(i):
        if not isinstance(i, dict):
            raise TypeError('Unexpected input type for <{}>'.format(type(i).__name__))
        return str(i.get('va', ''))

    @staticmethod
    def __decode_timerange(i):
        if not isinstance(i, dict):
            raise TypeError('Unexpected input type for <{}>'.format(type(i).__name__))
        style = i.get('s')
        # un = {}
        if style == 'GRIB1':
            un = {
                0: 'm',
                1: 'h',
                2: 'd',
                3: 'mo',
                4: 'y',
                5: 'de',
                6: 'no',
                7: 'ce',
                10: 'h3',
                11: 'h6',
                12: 'h12',
                254: 's'
            }
            return 'GRIB1,{type},{p1}{un},{p2}{un}'.format(
                type=i.get('ty'),
                p1=i.get('p1'),
                p2=i.get('p2'),
                un=un[i.get('un')]
            )
        elif style == 'GRIB2':
            un = {
                0: 'm',
                1: 'h',
                2: 'd',
                3: 'mo',
                4: 'y',
                5: 'de',
                6: 'no',
                7: 'ce',
                10: 'h3',
                11: 'h6',
                12: 'h12',
                254: 's'
            }
            return 'GRIB2,{type},{p1}{un},{p2}{un}'.format(
                type=i.get('ty'),
                p1=i.get('p1'),
                p2=i.get('p2'),
                un=un[i.get('un')]
            )
        elif style == 'Timedef':
            un = {
                0: 'm',
                1: 'h',
                2: 'd',
                3: 'mo',
                4: 'y',
                5: 'de',
                6: 'no',
                7: 'ce',
                10: 'h3',
                11: 'h6',
                12: 'h12',
                13: 's'
            }
            s = "Timedef"
            if i.get('su') == 255:
                s = ''.join([s, ',-'])
            else:
                s = ''.join([s, ',-{}{}'.format(i.get('sl'), un[i.get('un')])])
            if i.get('pt'):
                s = ''.join([s, ',{}'.format(i.get('pt'))])
            else:
                '''
                If i.pt is not defined, then the stat type is 255 and i.pl, i.pu are not defined too
                (see arki / types / timerange.cc:1358).
                If the stat type is 255, then proctype = "-"
                (see arki / types / timerange.cc:1403).
                '''
                s = ''.join([s, ',-'])

            '''
            If i.pu is not defined, then the stat unit is UNIT_MISSING = 255 and i.pl is not defined too
            (see arki / types / timerange.cc:1361).
            If stat unit is 255, then proclen = "-"
            (see arki / types / timerange.cc:1408).
            '''
            if i.get('pu'):
                s = ''.join([s, ',{}{}'.format(i.get('pl'), un[i.get('un')])])
            else:
                s = ''.join([s, ',-'])
            return s
        elif style == 'BUFR':
            un = {
                0: 'm',
                1: 'h',
                2: 'd',
                3: 'mo',
                4: 'y',
                5: 'de',
                6: 'no',
                7: 'ce',
                10: 'h3',
                11: 'h6',
                12: 'h12',
                13: 's'
            }
            return 'BUFR,{val}{un}'.format(
                val=i.get('va'),
                un=un[i.get('un')]
            )
        else:
            raise ValueError('Invalid <timerange> style for {}'.format(style))
