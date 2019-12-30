# -*- coding: utf-8 -*-

import shlex
import subprocess
import os
import datetime
import shutil
import glob
from pathlib import Path
from restapi.flask_ext.flask_celery import CeleryExt
from restapi.services.mail import send_mail, get_html_template
from restapi.confs import UPLOAD_FOLDER
from celery import states
from celery.exceptions import Ignore
from mistral.services.arkimet import DATASET_ROOT, BeArkimet as arki
from mistral.services.requests_manager import RequestManager
from mistral.exceptions import DiskQuotaException
from mistral.exceptions import PostProcessingException

from mistral.tools import derived_variables as pp1
from mistral.tools import statistic_elaboration as pp2
from mistral.tools import grid_interpolation as pp3_1
from mistral.tools import grid_cropping as pp3_2
from mistral.tools import spare_point_interpol as pp3_3

from restapi.utilities.logs import get_logger

celery_app = CeleryExt.celery_app

logger = get_logger(__name__)
DOWNLOAD_DIR = '/data'


@celery_app.task(bind=True)
# @send_errors_by_email
def data_extract(self, user_id, datasets, reftime=None, filters=None, postprocessors=[], request_id=None,
                 schedule_id=None):
    with celery_app.app.app_context():
        logger.info("Start task [{}:{}]".format(self.request.id, self.name))
        extra_msg = ''
        try:
            db = celery_app.get_service('sqlalchemy')
            schedule = None
            if schedule_id is not None:
                # load schedule for this request
                schedule = db.Schedule.query.get(schedule_id)
                if schedule is None:
                    raise ReferenceError("Cannot find schedule reference for task %s" % self.request.id)

                # create an entry in request db linked to the scheduled request entry
                product_name = RequestManager.get_schedule_name(db, schedule_id)
                request = RequestManager.create_request_record(db, user_id, product_name, {
                    'datasets': datasets,
                    'filters': filters,
                    'postprocessors': postprocessors
                }, schedule_id=schedule_id)
                # update the entry with celery task id
                request.task_id = self.request.id
                request_id = request.id
                db.session.commit()
                logger.debug('Schedule at: {}, Request <ID:{}>'.format(schedule_id, request.id))
            else:
                # load request by id
                request = db.Request.query.get(request_id)
                if request is None:
                    raise ReferenceError("Cannot find request reference for task %s" % self.request.id)

            query = ''  # default to no matchers
            if filters is not None:
                query = arki.parse_matchers(filters)
                logger.debug('Arkimet query: {}'.format(query))
            if reftime is not None:
                reftime_query = arki.parse_reftime(reftime['from'], reftime['to'])
                query = ";".join([reftime_query, query]) if query != '' else reftime_query

            # I should check the user quota before...
            # check the output size
            esti_data_size = arki.estimate_data_size(datasets, query)
            logger.debug('Resulting output size: {} ({})'.format(esti_data_size, human_size(esti_data_size)))

            # create download user dir if it doesn't exist
            uuid = RequestManager.get_uuid(db, user_id)
            user_dir = os.path.join(DOWNLOAD_DIR, uuid)
            os.makedirs(user_dir, exist_ok=True)

            # check for current used space
            used_quota = int(subprocess.check_output(['du', '-sb', user_dir]).split()[0])
            logger.info('Current used space: {} ({})'.format(used_quota, human_size(used_quota)))

            # check for exceeding quota
            max_user_quota = db.session.query(db.User.disk_quota).filter_by(id=user_id).scalar()
            logger.debug('MAX USER QUOTA for user<{}>: {}'.format(user_id, max_user_quota))
            if used_quota + esti_data_size > max_user_quota:
                free_space = max(max_user_quota - used_quota, 0)
                # save error message in db
                message = 'Disk quota exceeded: required size {}; remaining space {}'.format(
                    human_size(esti_data_size), human_size(free_space))
                # check if this request comes from a schedule. If so deactivate the schedule.
                if schedule:
                    logger.debug('Deactivate periodic task for schedule {}'.format(schedule_id))
                    if not CeleryExt.delete_periodic_task(name=str(schedule_id)):
                        raise Exception('Cannot delete periodic task for schedule {}'.format(schedule_id))
                    RequestManager.update_schedule_status(db, schedule_id, False)
                    extra_msg = '<br/><br/>Schedule "{}" temporary disabled for limit quota exceeded.'.format(schedule.name)
                raise DiskQuotaException(message)

            '''
             $ arki-query [OPZIONI] QUERY DATASET...
            '''
            ds = ' '.join([DATASET_ROOT + '{}'.format(i) for i in datasets])
            arki_query_cmd = shlex.split("arki-query --data '{}' {}".format(query, ds))
            logger.debug(arki_query_cmd)

            # output filename in the user space
            # max filename len = 64
            out_filename = 'data-{utc_now}-{id}.grib'.format(
                utc_now=datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ"),
                id=self.request.id)
            response = ''
            if postprocessors:
                logger.debug(postprocessors)
                #check if requested postprocessors are enabled
                for p in postprocessors:
                    pp_type = p.get('type')
                    enabled_postprocessors = (
                        'derived_variables', 'grid_interpolation', 'grid_cropping', 'spare_point_interpolation',
                        'statistic_elaboration')
                    if pp_type not in enabled_postprocessors:
                        raise ValueError("Unknown post-processor: {}".format(pp_type))

                    logger.debug('Data extraction with post-processing <{}>'.format(pp_type))

                # temporarily save the data extraction output
                tmp_outfile = os.path.join(user_dir, out_filename + '.tmp')
                # call data extraction
                with open(tmp_outfile, mode='w') as query_outfile:
                    ext_proc = subprocess.Popen(arki_query_cmd, stdout=query_outfile)
                    ext_proc.wait()
                    if ext_proc.wait() != 0:
                        raise Exception('Failure in data extraction')
                # final result
                outfile = os.path.join(user_dir, out_filename)

                # case of single postprocessor
                if len(postprocessors) == 1:
                    try:
                        p = postprocessors[0]
                        pp_type = p.get('type')

                        if pp_type == 'derived_variables':
                            pp1_output = pp1.pp_derived_variables(datasets=datasets, params=p, tmp_extraction=tmp_outfile, query=query, user_dir=user_dir)
                            # join pp1_output and tmp_extraction in output file
                            cat_cmd = ['cat',tmp_outfile,pp1_output]
                            with open(outfile,mode='w') as outfile:
                                ext_proc = subprocess.Popen(cat_cmd, stdout=outfile)
                                ext_proc.wait()
                                if ext_proc.wait() != 0:
                                    raise Exception('Failure in data extraction')

                        elif pp_type == 'statistic_elaboration':
                            params = []
                            params.append(p)
                            pp2.pp_statistic_elaboration(params=params, input=tmp_outfile, output=outfile)

                        elif pp_type == 'grid_interpolation':
                            pp3_1.pp_grid_interpolation(params=p, input=tmp_outfile, output=outfile)

                        elif pp_type == 'grid_cropping':
                            pp3_2.pp_grid_cropping(params=p, input=tmp_outfile, output=outfile)

                        elif pp_type == 'spare_point_interpolation':
                            #change output extension from .grib to .BUFR
                            outfile_name, outfile_ext = os.path.splitext(outfile)
                            bufr_outfile = outfile_name+'.BUFR'
                            pp3_3.pp_sp_interpolation(params=p, input=tmp_outfile, output=bufr_outfile)

                    finally:
                        # always remove tmp file
                        tmp_filelist = glob.glob(os.path.join(user_dir, "*.tmp"))
                        for f in tmp_filelist:
                            os.remove(f)
                        # if pp_type == 'spare_point_interpolation':
                        #     # remove the temporary folder where the files for the interpolation were uploaded
                        #     uploaded_filepath = Path(p.get('coord-filepath'))
                        #     shutil.rmtree(uploaded_filepath.parent)

                # case of multiple postprocessor
                else:
                    #check if there is only one geographical postprocessor
                    pp_list=[]
                    for p in postprocessors:
                        pp_list.append(p['type'])
                    pp3_list=['grid_cropping','grid_interpolation','spare_point_interpolation']
                    if len(set(pp_list).intersection(set(pp3_list))) > 1:
                        raise PostProcessingException('Only one geographical postprocessing at a time can be executed')
                    try:
                        tmp_extraction_basename = os.path.basename(tmp_outfile)
                        pp_output = None
                        if any(d['type'] == 'derived_variables' for d in postprocessors):
                            p = next(item for item in postprocessors if item["type"] == 'derived_variables')
                            pp1_output = pp1.pp_derived_variables(datasets=datasets, params=p,
                                                             tmp_extraction=tmp_outfile, query=query,
                                                             user_dir=user_dir)
                            # join pp1_output and tmp_extraction in output file
                            cat_cmd = ['cat', tmp_outfile, pp1_output]
                            # new temp file as pp output
                            new_tmp_extraction_filename = tmp_extraction_basename.split('.')[0] + '-pp1.grib.tmp'
                            pp_output = os.path.join(user_dir, new_tmp_extraction_filename)
                            with open(pp_output, mode='w') as pp1_outfile:
                                ext_proc = subprocess.Popen(cat_cmd, stdout=pp1_outfile)
                                ext_proc.wait()
                                if ext_proc.wait() != 0:
                                    raise Exception('Failure in data extraction')
                        if any(d['type'] == 'statistic_elaboration' for d in postprocessors):
                            p=[]
                            for item in postprocessors:
                                if item["type"] == 'statistic_elaboration':
                                    p.append(item)
                            #check if the input has to be the previous postprocess output
                            pp_input = ''
                            if pp_output is not None:
                                pp_input = pp_output
                            else:
                                pp_input = tmp_outfile
                            new_tmp_extraction_filename = tmp_extraction_basename.split('.')[0] + '-pp2.grib.tmp'
                            pp_output = os.path.join(user_dir, new_tmp_extraction_filename)
                            pp2.pp_statistic_elaboration(params=p, input=pp_input, output=pp_output)
                        if any(d['type'] == 'grid_cropping' for d in postprocessors):
                            p = next(item for item in postprocessors if item["type"] == 'grid_cropping')
                            # check if the input has to be the previous postprocess output
                            pp_input = ''
                            if pp_output is not None:
                                pp_input = pp_output
                            else:
                                pp_input = tmp_outfile
                            new_tmp_extraction_filename = tmp_extraction_basename.split('.')[0] + '-pp3_2.grib.tmp'
                            pp_output = os.path.join(user_dir, new_tmp_extraction_filename)
                            pp3_2.pp_grid_cropping(params=p, input=pp_input, output=pp_output)
                        if any(d['type'] == 'grid_interpolation' for d in postprocessors):
                            p = next(item for item in postprocessors if item["type"] == 'grid_interpolation')
                            # check if the input has to be the previous postprocess output
                            pp_input = ''
                            if pp_output is not None:
                                pp_input = pp_output
                            else:
                                pp_input = tmp_outfile
                            new_tmp_extraction_filename = tmp_extraction_basename.split('.')[0] + '-pp3_1.grib.tmp'
                            pp_output = os.path.join(user_dir, new_tmp_extraction_filename)
                            pp3_1.pp_grid_interpolation(params=p, input=input, output=pp_output)
                        if any(d['type'] == 'spare_point_interpolation' for d in postprocessors):
                            p = next(item for item in postprocessors if item["type"] == 'spare_point_interpolation')
                            # check if the input has to be the previous postprocess output
                            pp_input = ''
                            if pp_output is not None:
                                pp_input = pp_output
                            else:
                                pp_input = tmp_outfile
                            #new_tmp_extraction_filename = tmp_extraction_basename.split('.')[0] + '-pp3_3.grib.tmp'
                            new_tmp_extraction_filename = tmp_extraction_basename.split('.')[0] + '.bufr'
                            pp_output = os.path.join(user_dir, new_tmp_extraction_filename)
                            pp3_3.pp_sp_interpolation(params=p, input=pp_input, output=pp_output)
                        # rename the final output of postprocessors as outfile unless it is not a bufr file
                        if pp_output.split('.')[-1]!='bufr':
                            logger.debug('dest: {}'.format(str(outfile)))
                            os.rename(pp_output,outfile)
                    finally:
                        # remove all tmp file
                        tmp_filelist= glob.glob(os.path.join(user_dir, "*.tmp"))
                        for f in tmp_filelist:
                            os.remove(f)
                        # if there is, remove the temporary folder where the files for the sp_interpolation were uploaded
                        # if os.path.isdir(os.path.join(UPLOAD_FOLDER,uuid)):
                        #     shutil.rmtree(os.path.join(UPLOAD_FOLDER,uuid))
            else:
                with open(os.path.join(user_dir, out_filename), mode='w') as outfile:
                    subprocess.Popen(arki_query_cmd, stdout=outfile)

            # get the actual data size
            data_size = os.path.getsize(os.path.join(user_dir, out_filename))
            if data_size > esti_data_size:
                logger.warn('Actual resulting data exceeds estimation of {}'.format(
                    human_size(data_size - esti_data_size)))
            # create fileoutput record in db
            RequestManager.create_fileoutput_record(db, user_id, request_id, out_filename, data_size)
            # update request status
            request.status = states.SUCCESS

        except DiskQuotaException as exc:
            request.status = states.FAILURE
            request.error_message = str(exc)
            logger.warn(str(exc))
            # manually update the task state
            self.update_state(
                state=states.FAILURE,
                meta=message
            )
            raise Ignore()
        except PostProcessingException as exc:
            request.status = states.FAILURE
            request.error_message = str(exc)
            logger.warn(str(exc))
            # manually update the task state
            self.update_state(
                state=states.FAILURE,
                meta=str(exc)
            )
            raise Ignore()
        except Exception as exc:
            # handle all the other exceptions
            request.status = states.FAILURE
            request.error_message = 'Failed to extract data'
            logger.exception('Failed to extract data: %r', exc)
            raise exc
        finally:
            request.end_date = datetime.datetime.utcnow()
            db.session.commit()
            logger.info('Terminate task {} with state {}'.format(self.request.id, request.status))
            # user notification via email
            user_email = db.session.query(db.User.email).filter_by(id=user_id).scalar()
            body_msg = request.error_message if request.error_message is not None else "Your data is ready for " \
                                                                                       "downloading"
            body_msg += extra_msg
            send_result_notication(user_email, request.status, body_msg)


def send_result_notication(recipient, status, message):
    """Send email notification. """
    replaces = {
        "status": status,
        "message": message
    }
    body = get_html_template("data_extraction_result.html", replaces)
    send_mail(
        body,
        "MeteoHub: data extraction completed",
        recipient,
        plain_body=body
    )


def human_size(bytes, units=[' bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB']):
    """ Returns a human readable string reprentation of bytes
    :rtype: string
    """
    return str(bytes) + units[0] if bytes < 1024 else human_size(bytes >> 10, units[1:])

