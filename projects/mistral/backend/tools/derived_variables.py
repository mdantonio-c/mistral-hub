import os
import shlex
import subprocess

from mistral.exceptions import PostProcessingException
from restapi.utilities.logs import log


def pp_derived_variables(datasets, params, tmp_extraction, user_dir, fileformat):
    log.debug("Derived variable postprocessor")

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
        # command for postprocessor
        if fileformat.startswith("grib"):
            pp1_output_filename = (
                tmp_extraction_basename.split(".")[0] + "-pp1_output.grib.tmp"
            )
        else:
            pp1_output_filename = (
                tmp_extraction_basename.split(".")[0] + "-pp1_output.bufr.tmp"
            )
        pp1_output = os.path.join(user_dir, pp1_output_filename)
        libsim_tool = ""
        if fileformat.startswith("grib"):
            libsim_tool = "vg6d_transform"
        else:
            libsim_tool = "v7d_transform"
        post_proc_cmd = shlex.split(
            "{} --output-variable-list={} {} {} {}".format(
                libsim_tool,
                ",".join(params.get("variables")),
                "--input-format=BUFR --output-format=BUFR"
                if libsim_tool == "v7d_transform"
                else "",
                tmp_outfile,
                pp1_output,
            )
        )
        log.debug("funziona?")
        log.debug("Post process command: {}>", post_proc_cmd)

        proc = subprocess.Popen(post_proc_cmd)
        # wait for the process to terminate
        if proc.wait() != 0:
            raise Exception("Failure in post-processing")
        else:
            return pp1_output

    except Exception as perr:
        log.warning(perr)
        message = "Error in post-processing: no results"
        raise PostProcessingException(message)
    # ------ correcting the choice of filters in order to always obtain a result for postprocessing ----- not necessary at the moment
    # finally:
    #     if new_tmp_extraction is not None:
    #         os.remove(new_tmp_extraction)
    # -----------------------------------------------
