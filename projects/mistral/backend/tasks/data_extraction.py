# -*- coding: utf-8 -*-

import shlex
import subprocess
import os
import datetime
# import shutil
import glob
# from pathlib import Path
from restapi.flask_ext.flask_celery import CeleryExt
from restapi.services.mail import send_mail
from restapi.utilities.templates import get_html_template
# from restapi.confs import UPLOAD_FOLDER
from celery import states
from celery.exceptions import Ignore
from mistral.services.arkimet import DATASET_ROOT, BeArkimet as arki
from mistral.services.requests_manager import RequestManager

from restapi.utilities.logs import log

celery_app = CeleryExt.celery_app

DOWNLOAD_DIR = '/data'


@celery_app.task(bind=True)
# @send_errors_by_email
def data_extract(self, user_id, datasets, reftime=None, filters=None, postprocessors=[], request_id=None,
                 schedule_id=None):
    with celery_app.app.app_context():
        log.info("Start task [{}:{}]", self.request.id, self.name)
        extra_msg = ''
        try:
            db = celery_app.get_service('sqlalchemy')
            schedule = None
            if schedule_id is not None:
                # load schedule for this request
                schedule = db.Schedule.query.get(schedule_id)
                if schedule is None:
                    raise ReferenceError(
                        "Cannot find schedule reference for task {}".format(
                            self.request.id))

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
                log.debug('Schedule at: {}, Request <ID:{}>', schedule_id, request.id)
            else:
                # load request by id
                request = db.Request.query.get(request_id)
                if request is None:
                    raise ReferenceError("Cannot find request reference for task {}".format(self.request.id))

            query = ''  # default to no matchers
            if filters is not None:
                query = arki.parse_matchers(filters)
                log.debug('Arkimet query: {}', query)
            if reftime is not None:
                reftime_query = arki.parse_reftime(reftime['from'], reftime['to'])
                query = ";".join([reftime_query, query]) if query != '' else reftime_query

            # I should check the user quota before...
            # check the output size
            esti_data_size = arki.estimate_data_size(datasets, query)
            log.debug('Resulting output size: {} ({})', esti_data_size, human_size(esti_data_size))

            # create download user dir if it doesn't exist
            uuid = RequestManager.get_uuid(db, user_id)
            user_dir = os.path.join(DOWNLOAD_DIR, uuid)
            os.makedirs(user_dir, exist_ok=True)

            # check for current used space
            used_quota = int(subprocess.check_output(['du', '-sb', user_dir]).split()[0])
            log.info('Current used space: {} ({})', used_quota, human_size(used_quota))

            # check for exceeding quota
            max_user_quota = db.session.query(db.User.disk_quota).filter_by(id=user_id).scalar()
            log.debug('MAX USER QUOTA for user<{}>: {}', user_id, max_user_quota)
            if used_quota + esti_data_size > max_user_quota:
                free_space = max(max_user_quota - used_quota, 0)
                # save error message in db
                message = 'Disk quota exceeded: required size {}; remaining space {}'.format(
                    human_size(esti_data_size), human_size(free_space))
                # check if this request comes from a schedule. If so deactivate the schedule.
                if schedule:
                    log.debug('Deactivate periodic task for schedule {}', schedule_id)
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
            log.debug(arki_query_cmd)

            # output filename in the user space
            # max filename len = 64
            out_filename = 'data-{utc_now}-{id}.grib'.format(
                utc_now=datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ"),
                id=self.request.id)
            # response = ''
            if postprocessors:
                log.debug(postprocessors)
                # check if requested postprocessors are enabled
                for p in postprocessors:
                    pp_type = p.get('type')
                    enabled_postprocessors = (
                        'derived_variables', 'grid_interpolation', 'grid_cropping', 'spare_point_interpolation',
                        'statistic_elaboration')
                    if pp_type not in enabled_postprocessors:
                        raise ValueError("Unknown post-processor: {}", pp_type)

                    log.debug(
                        'Data extraction with post-processing <{}>', pp_type)

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
                            pp1_output = pp_derived_variables(datasets=datasets, params=p, tmp_extraction=tmp_outfile, query=query, user_dir=user_dir)
                            # join pp1_output and tmp_extraction in output file
                            cat_cmd = ['cat',tmp_outfile,pp1_output]
                            with open(outfile,mode='w') as outfile:
                                ext_proc = subprocess.Popen(cat_cmd, stdout=outfile)
                                ext_proc.wait()
                                if ext_proc.wait() != 0:
                                    raise Exception('Failure in data extraction')
                            # delete pp1_output
                            os.remove(pp1_output)

                        elif pp_type == 'grid_interpolation':
                            pp_grid_interpolation(params=p, input=tmp_outfile, output=outfile)

                        elif pp_type == 'grid_cropping':
                            pp_grid_cropping(params=p, input=tmp_outfile, output=outfile)

                        elif pp_type == 'spare_point_interpolation':
                            #change output extension from .grib to .BUFR
                            outfile_name, outfile_ext = os.path.splitext(outfile)
                            bufr_outfile = outfile_name+'.BUFR'
                            pp_sp_interpolation(params=p, input=tmp_outfile, output=bufr_outfile)

                        elif pp_type == 'statistic_elaboration':
                            pp_statistic_elaboration(params=p, input=tmp_outfile, output=outfile)

                    finally:
                        # always remove tmp file
                        os.remove(tmp_outfile)
                        # if pp_type == 'spare_point_interpolation':
                        #     # remove the temporary folder where the files for the intepolation were uploaded
                        #     uploaded_filepath = Path(p.get('coord-filepath'))
                        #     shutil.rmtree(uploaded_filepath.parent)
                # case of multiple postprocessor
                else:
                    try:
                        tmp_extraction_basename = os.path.basename(tmp_outfile)
                        pp_output = None
                        if any(d['type'] == 'derived_variables' for d in postprocessors):
                            p = next(item for item in postprocessors if item["type"] == 'derived_variables')
                            pp1_output = pp_derived_variables(datasets=datasets, params=p,
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
                            # delete pp1_output
                            os.remove(pp1_output)
                        if any(d['type'] == 'statistic_elaboration' for d in postprocessors):
                            p = next(item for item in postprocessors if item["type"] == 'statistic_elaboration')
                            #check if the input has to be the previous postprocess output
                            pp_input = ''
                            if pp_output is not None:
                                pp_input = pp_output
                            else:
                                pp_input = tmp_outfile
                            new_tmp_extraction_filename = tmp_extraction_basename.split('.')[0] + '-pp2.grib.tmp'
                            pp_output = os.path.join(user_dir, new_tmp_extraction_filename)
                            pp_statistic_elaboration(params=p, input=pp_input, output=pp_output)
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
                            pp_grid_cropping(params=p, input=pp_input, output=pp_output)
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
                            pp_grid_interpolation(params=p, input=input, output=pp_output)
                        if any(d['type'] == 'spare_point_interpolation' for d in postprocessors):
                            p = next(item for item in postprocessors if item["type"] == 'spare_point_interpolation')
                            # check if the input has to be the previous postprocess output
                            pp_input = ''
                            if pp_output is not None:
                                pp_input = pp_output
                            else:
                                pp_input = tmp_outfile
                            #new_tmp_extraction_filename = tmp_extraction_basename.split('.')[0] + '-pp3_3.grib.tmp'
                            new_tmp_extraction_filename = tmp_extraction_basename.split('.')[0] + '.BUFR'
                            pp_output = os.path.join(user_dir, new_tmp_extraction_filename)
                            pp_sp_interpolation(params=p, input=pp_input, output=pp_output)
                        # rename the final output of postprocessors as outfile
                        log.debug('dest: {}', outfile)
                        os.rename(pp_output, outfile)
                    finally:
                        # remove all tmp file
                        tmp_filelist = glob.glob(os.path.join(user_dir, "*.tmp"))
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
                log.warning(
                    'Actual resulting data exceeds estimation of {}',
                    human_size(data_size - esti_data_size)
                )
            # create fileoutput record in db
            RequestManager.create_fileoutput_record(db, user_id, request_id, out_filename, data_size)
            # update request status
            request.status = states.SUCCESS

        except DiskQuotaException as exc:
            request.status = states.FAILURE
            request.error_message = str(exc)
            log.warning(str(exc))
            # manually update the task state
            self.update_state(
                state=states.FAILURE,
                meta=message
            )
            raise Ignore()
        except PostProcessingException as exc:
            request.status = states.FAILURE
            request.error_message = str(exc)
            log.warning(str(exc))
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
            log.exception('Failed to extract data: {}', repr(exc))
            raise exc
        finally:
            request.end_date = datetime.datetime.utcnow()
            db.session.commit()
            log.info('Terminate task {} with state {}', self.request.id, request.status)
            # user notification via email
            user_email = db.session.query(db.User.email).filter_by(id=user_id).scalar()
            body_msg = request.error_message if request.error_message is not None else "Your data is ready for " \
                                                                                       "downloading"
            body_msg += extra_msg
            send_result_notication(user_email, request.status, body_msg)

def pp_derived_variables(datasets, params, tmp_extraction, query, user_dir):
    log.debug('Derived variable postprocessor')

    # ------ correcting the choice of filters in order to always obtain a result for postprocessing ----- not necessary at the moment
    # product_query = []
    # level_query = []
    # # products for wind direction and wind speed
    # if ('B11001' or 'B11002') in params.get('variables'):
    #     # u-component
    #     product_query.append('GRIB1,80,2,33')
    #     # v-component
    #     product_query.append('GRIB1,80,2,34')
    #     # level 10
    #     level_query.append('GRIB1,105,10')
    # # products for relative humidity
    # if 'B13003' in params.get('variables'):
    #     # temperature
    #     product_query.append('GRIB1,80,2,11')
    #     # specific humidity
    #     product_query.append('GRIB1,80,2,51')
    #     # pressure
    #     product_query.append('GRIB1,80,2,1')
    #     # level 0
    #     level_query.append('GRIB1,1')
    # # products for snowfall
    # if 'B13205' in params.get('variables'):
    #     # grid scale snowfall
    #     product_query.append('GRIB1,80,2,79')
    #     # convective snowfall
    #     product_query.append('GRIB1,80,2,78')
    #     # level 0
    #     level_query.append('GRIB1,1')
    # # products for u-component (--> is already in the dataset products..)
    # if 'B11003' in params.get('variables'):
    #     # u-component
    #     product_query.append('GRIB1,80,2,33')
    #     # level 10
    #     level_query.append('GRIB1,105,10')
    # # products for v-component (--> is already in the dataset products..)
    # if 'B11004' in params.get('variables'):
    #     # v-component
    #     product_query.append('GRIB1,80,2,34')
    #     # level 10
    #     level_query.append('GRIB1,105,10')
    # # products for dew-point temperature (--> is already in the dataset products..)
    # if 'B12103' in params.get('variables'):
    #     # dew-point temperature
    #     product_query.append('GRIB1,80,2,17')
    # # products for specific humidity (--> is already in the dataset products..)
    # if 'B13001' in params.get('variables'):
    #     # specific humidity
    #     product_query.append('GRIB1,80,2,51')
    #     # level 0
    #     level_query.append('GRIB1,1')
    # # air density??
    #
    # log.debug('Products needed for pp : {}', product_query)
    # log.debug('Levels needed for pp : {}', level_query)
    # --------------------------------------------------------------------

    try:
        tmp_extraction_basename = os.path.basename(tmp_extraction)
        # ------ correcting the choice of filters in order to always obtain a result for postprocessing ----- not necessary at the moment
        # new_tmp_extraction = None
        # # check if requested products are already in the query
        # actual_filter_list = [x.strip() for x in query.split(';')]
        # actual_products = [i.split(":")[1] for i in actual_filter_list if i.startswith('product')]
        # if not all(elem in [x.strip() for x in actual_products[0].split('or')] for elem in product_query):
        #     # products requested for postprocessing
        #     pp_products = " or ".join(product_query)
        #     # replace the products in query
        #     new_filter_list_w_product = ['product:'+pp_products if i.startswith('product') else i for i in actual_filter_list]
        #     new_query_w_product = ";".join(new_filter_list_w_product)
        #     log.debug('Query for pp with new products: {}', new_query_w_product)
        #     # check if the new query gives back some results
        #     summary = arki.load_summary(datasets, new_query_w_product)
        #     # if not replace also the level param
        #     if summary['items']['summarystats']['s']==0 :
        #         pp_levels = " or ".join(level_query)
        #         # replace the levels in query
        #         actual_filter_list = [x.strip() for x in new_query_w_product.split(';')]
        #         new_filter_list_w_level = ['level:' + pp_levels if i.startswith('level') else i for i in
        #                                      actual_filter_list]
        #         new_query_w_level = ";".join(new_filter_list_w_level)
        #         log.debug('Query for pp with new levels: {}', new_query_w_level)
        #         # check if the new query gives back some results
        #         summary = arki.load_summary(datasets, new_query_w_level)
        #         # if not raise error
        #         if summary['items']['summarystats']['s'] == 0:
        #             raise Exception('Failure in post-processing')
        #         # if the new query with the new levels is correct, replace the old one
        #         else:
        #             query = new_query_w_level
        #     # if the new query with the new products is correct, replace the old one
        #     else:
        #         query = new_query_w_product
        #     # temporarily save the data extraction output of the new query
        #     ds = ' '.join([DATASET_ROOT + '{}'.format(i) for i in datasets])
        #     arki_query_cmd = shlex.split("arki-query --data '{}' {}".format(query, ds))
        #     new_tmp_extraction_filename = tmp_extraction_basename.split('.')[0]+'-new_temp_extr.grib.tmp'
        #     new_tmp_extraction = os.path.join(user_dir,new_tmp_extraction_filename)
        #     # call data extraction
        #     with open(new_tmp_extraction, mode='w') as query_outfile:
        #         ext_proc = subprocess.Popen(arki_query_cmd, stdout=query_outfile)
        #         ext_proc.wait()
        #         if ext_proc.wait() != 0:
        #             raise Exception('Failure in data extraction with parameters for derived variables')
        # # set the correct input file for postprocessing
        # if new_tmp_extraction is not None:
        #     tmp_outfile = new_tmp_extraction
        # else:
        #     tmp_outfile = tmp_extraction
        # --------------------------------------------------------------------

        tmp_outfile = tmp_extraction
        #command for postprocessor
        pp1_output_filename = tmp_extraction_basename.split('.')[0]+'-pp1_output.grib.tmp'
        pp1_output = os.path.join(user_dir,pp1_output_filename)
        post_proc_cmd = shlex.split("vg6d_transform --output-variable-list={} {} {}".format(
            ",".join(params.get('variables')),
            tmp_outfile,
            pp1_output)
        )
        log.debug('Post process command: {}>', post_proc_cmd)

        proc = subprocess.Popen(post_proc_cmd)
        # wait for the process to terminate
        if proc.wait() != 0:
            raise Exception('Failure in post-processing')
        else:
            return pp1_output

    except Exception as perr:
        log.warn(str(perr))
        message = 'Error in post-processing: no results'
        raise PostProcessingException(message)
    # ------ correcting the choice of filters in order to always obtain a result for postprocessing ----- not necessary at the moment
    # finally:
    #     if new_tmp_extraction is not None:
    #         os.remove(new_tmp_extraction)
    #-----------------------------------------------

def pp_grid_interpolation(params, input, output):
    log.debug('Grid interpolation postprocessor')
    try:
        post_proc_cmd =[]
        post_proc_cmd.append('vg6d_transform')
        post_proc_cmd.append('--trans-type={}'.format(params.get('trans-type')))
        post_proc_cmd.append('--sub-type={}'.format(params.get('sub-type')))

        # check if there is a grib file template. If not, looks for others interpolation params
        if 'template' in params:
            post_proc_cmd.append('--output-format=grib_api:{}'.format(params['template']))
        else:
            # vg6d_transform automatically provides defaults for missing optional params
            if 'boundings' in params:
                if 'x-min' in params['boundings']:
                    post_proc_cmd.append('--x-min={}'.format(params['boundings']['x-min']))
                if 'x-max' in params['boundings']:
                    post_proc_cmd.append('--x-max={}'.format(params['boundings']['x-max']))
                if 'y-min' in params['boundings']:
                    post_proc_cmd.append('--y-min={}'.format(params['boundings']['y-min']))
                if 'y-max' in params['boundings']:
                    post_proc_cmd.append('--y-max={}'.format(params['boundings']['y-max']))
            if 'nodes' in params:
                if 'nx' in params['nodes']:
                    post_proc_cmd.append('--nx={}'.format(params['nodes']['nx']))
                if 'ny' in params['nodes']:
                    post_proc_cmd.append('--ny={}'.format(params['nodes']['ny']))

        # post_proc_cmd.append('--display')
        post_proc_cmd.append(input)
        post_proc_cmd.append(output)
        log.debug('Post process command: {}>', post_proc_cmd)

        proc = subprocess.Popen(post_proc_cmd)
        # wait for the process to terminate
        if proc.wait() != 0:
            raise Exception('Failure in post-processing')
        else:
            return output

    except Exception as perr:
        log.warn(str(perr))
        message = 'Error in post-processing: no results'
        raise PostProcessingException(message)

def pp_grid_cropping(params, input, output):
    log.debug('Grid cropping postprocessor')
    try:
        post_proc_cmd = []
        post_proc_cmd.append('vg6d_transform')
        post_proc_cmd.append('--trans-type={}'.format(params.get('trans-type')))
        post_proc_cmd.append('--sub-type={}'.format(params.get('sub-type')))

        if 'ilon' in params['boundings']:
            post_proc_cmd.append('--ilon={}'.format(params['boundings']['ilon']))
        if 'ilat' in params['boundings']:
            post_proc_cmd.append('--ilat={}'.format(params['boundings']['ilat']))
        if 'flon' in params['boundings']:
            post_proc_cmd.append('--flon={}'.format(params['boundings']['flon']))
        if 'flat' in params['boundings']:
            post_proc_cmd.append('--flat={}'.format(params['boundings']['flat']))

        post_proc_cmd.append(input)
        post_proc_cmd.append(output)
        log.debug('Post process command: {}>', post_proc_cmd)

        proc = subprocess.Popen(post_proc_cmd)
        # wait for the process to terminate
        if proc.wait() != 0:
            raise Exception('Failure in post-processing')
        else:
            return output

    except Exception as perr:
        log.warn(str(perr))
        message = 'Error in post-processing: no results'
        raise PostProcessingException(message)

def pp_sp_interpolation(params, input, output):
    log.debug('Spare point interpolation postprocessor')
    try:
        post_proc_cmd = []
        post_proc_cmd.append('vg6d_getpoint')
        post_proc_cmd.append('--trans-type={}'.format(params.get('trans-type')))
        post_proc_cmd.append('--sub-type={}'.format(params.get('sub-type')))
        post_proc_cmd.append('--coord-file={}'.format(params.get('coord-filepath')))
        post_proc_cmd.append('--coord-format={}'.format(params.get('format')))
        post_proc_cmd.append(input)
        post_proc_cmd.append(output)
        log.debug('Post process command: {}>', post_proc_cmd)

        proc = subprocess.Popen(post_proc_cmd)
        # wait for the process to terminate
        if proc.wait() != 0:
            raise Exception('Failure in post-processing')
        else:
            return output

    except Exception as perr:
        log.warn(str(perr))
        message = 'Error in post-processing: no results'
        raise PostProcessingException(message)

def pp_statistic_elaboration(params, input, output):
    log.debug('Statistic elaboration postprocessor')
    step=""
    interval= params.get('interval')
    if interval=='years':
        step = "{:04d}000000 00:00:00.000".format(params.get('step'))
    if interval=='months':
        step = "0000{:02d}0000 00:00:00.000".format(params.get('step'))
    if interval=='days':
        step = "000000{:04d} 00:00:00.000".format(params.get('step'))
    if interval=='hours':
        step = "0000000000 {:02d}:00:00.000".format(params.get('step'))
    try:
        post_proc_cmd = []
        post_proc_cmd.append('vg6d_transform')
        post_proc_cmd.append('--comp-stat-proc={}:{}'.format(params.get('input-timerange'), params.get('output-timerange')))
        post_proc_cmd.append("--comp-step='{}'".format(step))
        post_proc_cmd.append(input)
        post_proc_cmd.append( output)
        log.debug('Post process command: {}>', post_proc_cmd)

        proc = subprocess.Popen(post_proc_cmd)
        # wait for the process to terminate
        if proc.wait() != 0:
            raise Exception('Failure in post-processing')
        else:
            return output

    except Exception as perr:
        log.warn(str(perr))
        message = 'Error in post-processing: no results'
        raise PostProcessingException(message)

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


class DiskQuotaException(Exception):
    """Exception for disk quota exceeding."""


class PostProcessingException(Exception):
    """Exception for post-processing failure."""
