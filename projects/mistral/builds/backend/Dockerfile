FROM rapydo/backend:2.4

ARG RAPYDO_VERSION
RUN test -n "$RAPYDO_VERSION"

ARG CURRENT_UID
RUN test -n "$CURRENT_UID"
ENV APIUSER developer

RUN usermod -u $CURRENT_UID $APIUSER

RUN echo "deb [trusted=yes] https://simc.arpae.it/packages/debian jammy main" > /etc/apt/sources.list.d/arpae-simc.list \
    && apt-get update -qq \
    && apt-get install -y python3-wreport dballe python3-dballe arkimet libsim python3-eccodes eccodes-simc dba-qcfilter gdal-bin libeccodes-tools

# add the custom formatter for GRIB2 files
RUN mkdir -p /etc/arkimet/format
COPY formatter_grib2.py /etc/arkimet/format/formatter_grib2.py
# check if the custom formatter compiles correctly
RUN python3 -m py_compile /etc/arkimet/format/formatter_grib2.py

RUN pip3 install --upgrade boto3 \
    && pip install 'boto3-stubs[s3]'

WORKDIR /code
