FROM arpaesimc/centos:8 AS arpaesimc

FROM rapydo/backend:1.2

ARG RAPYDO_VERSION
RUN test -n "$RAPYDO_VERSION"

ARG CURRENT_UID
RUN test -n "$CURRENT_UID"
ENV APIUSER developer

RUN usermod -u $CURRENT_UID $APIUSER

#########################################################
# Python 3.9 is not working for dballe, let's downgrade to python 3.8
ENV PYTHON_VERSION="3.8"
RUN ln -sf /usr/bin/python${PYTHON_VERSION} /usr/bin/python3 \
    && curl --silent https://bootstrap.pypa.io/get-pip.py --output get-pip.py \
    && python3 get-pip.py \
    && rm get-pip.py \
    && apt-get update \
    && apt-get install --yes python${PYTHON_VERSION}-dev \
    && pip3 install --upgrade --no-cache-dir git+https://github.com/rapydo/http-api.git@$RAPYDO_VERSION
#########################################################

RUN echo "deb http://security.ubuntu.com/ubuntu xenial-security main" >> /etc/apt/sources.list \
 && apt-get update \
 && apt-get install --yes \
      libssl1.0.0 \
      libssl-dev \
      libpopt-dev \
      liblzo2-2 \
      libx11-6 \
      libzip5 \
      gdal-bin \
      cmake \
      gfortran \
 && apt-get autoremove --yes \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

ENV PATH="$PATH:/usr/bin/centos"

ENV DATASET_ROOT="/arkimet/datasets/"

ENV ECCODES_VERSION="2.19.0"
ENV ECCODES_DIR="/usr/share/eccodes-build"

# With both definitions from arpaesimc
# ENV ECCODES_DEFINITION_PATH="/usr/share/eccodes-simc/definitions/:/usr/share/eccodes/definitions/"

# Only eccodes-simc from arpaesimc
ENV ECCODES_DEFINITION_PATH="/usr/share/eccodes-simc/definitions/:/usr/share/eccodes-build/share/eccodes/definitions/"

RUN wget --no-check-certificate "https://confluence.ecmwf.int/download/attachments/45757960/eccodes-${ECCODES_VERSION}-Source.tar.gz?api=v2" -O /tmp/eccodes-${ECCODES_VERSION}-Source.tar.gz \
  && cd /tmp \
  && tar -xzf eccodes-${ECCODES_VERSION}-Source.tar.gz \
  && mkdir /tmp/eccodes-build \
  && cd /tmp/eccodes-build \
  && cmake -DCMAKE_INSTALL_PREFIX=/usr/share/eccodes-build /tmp/eccodes-${ECCODES_VERSION}-Source \
  && make \
  && ctest \
  && make install \
  && cd /usr/share/eccodes-build \
  && ln -sf lib lib64 \
  && pip3 install eccodes netCDF4 \
  && rm -rf /tmp/eccodes-${ECCODES_VERSION}-Source.tar.gz \
  && rm -rf /tmp/eccodes-build

COPY --from=arpaesimc /usr/bin /usr/bin/centos

COPY --from=arpaesimc /etc/arkimet /etc/arkimet
# COPY --from=arpaesimc /usr/share/eccodes /usr/share/
COPY --from=arpaesimc /usr/share/eccodes-simc/definitions/ /usr/share/eccodes-simc/definitions/
# COPY --from=arpaesimc /usr/share/eccodes/definitions/ /usr/share/eccodes/definitions/
COPY --from=arpaesimc /usr/share/libsim/ /usr/share/libsim/
COPY --from=arpaesimc /usr/share/wreport/ /usr/share/wreport/

# arpaesimc/centos:7 -> 8

# Upgraded the following:
#     libpng15 -> libpng16
#     libgeos-3.4.2 -> libgeos-3.7.2
#     libxerces-c-3.1 -> libxerces-c-3.2
#     libsatlas -> atlas (folder, duplicated)
#     mysql -> libmariadb.so.3

# Removed the following:
#     libCharLS
#     libopenjpeg
#     libSM
#     libICE

# Added the following:
#     libarchive.so.13
#     libxapian.so.30
#     liblua-5.3.so
#     libreadline.so.7
#     libjasper.so.4
#     libmfhdf.so.0
#     libdf.so.0
#     libhdf5_hl.so.100
#     libhdf5.so.103
#     libtirpc.so.3
#     libopenblasp.so.0
#     libpq.so.5

COPY --from=arpaesimc /usr/lib64/libarkimet.* /usr/lib64/libdballe.* /usr/lib64/libmeteo-vm2.* /usr/lib64/libwreport.* /usr/lib64/libeccodes.* /usr/lib64/libeccodes_f90.* /usr/lib64/libsim_* /usr/lib64/libdballef.* /usr/lib64/libnetcdff.* /usr/lib64/libnetcdf.* /usr/lib64/liblog4fortran.* /usr/lib64/libfortrangis.* /usr/lib64/libfortranc.* /usr/lib64/libgfortran.* /usr/lib64/libgdal.* /usr/lib64/libproj.* /usr/lib64/libshp.* /usr/lib64/liblog4c.* /usr/lib64/libarmadillo.* /usr/lib64/libcfitsio.* /usr/lib64/libdap.so.* /usr/lib64/libdapclient.* /usr/lib64/libdapserver.* /usr/lib64/libfreexl.* /usr/lib64/libgeos-3.7.2.* /usr/lib64/libgeotiff.* /usr/lib64/libgif.* /usr/lib64/libgta.* /usr/lib64/libodbc.* /usr/lib64/libodbcinst.* /usr/lib64/libogdi.* /usr/lib64/libopenjp2.* /usr/lib64/libpcre.* /usr/lib64/libpoppler.* /usr/lib64/libwebp.* /usr/lib64/libxerces-c-3.2.* /usr/lib64/libopenblaso.* /usr/lib64/liblapack.* /usr/lib64/libarpack.* /usr/lib64/libsuperlu.* /usr/lib64/liblcms2.* /usr/lib64/libcrypto.* /usr/lib64/libssl.* /usr/lib64/libblas.* /usr/lib64/atlas /usr/lib64/libjpeg.* /usr/lib64/libpng16.* /usr/lib64/libarchive.so.13* /usr/lib64/libmariadb.so.3* /usr/lib64/libxapian.so.30* /usr/lib64/liblua-5.3.so* /usr/lib64/libreadline.so.7* /usr/lib64/libjasper.so.4* /usr/lib64/libmfhdf.so.0* /usr/lib64/libdf.so.0* /usr/lib64/libhdf5_hl.so.100* /usr/lib64/libhdf5.so.103* /usr/lib64/libtirpc.so.3* /usr/lib64/libopenblasp.so.0* /usr/lib64/libpq.so.5* /usr/lib/x86_64-linux-gnu/

COPY --from=arpaesimc /usr/lib64/python3.6/site-packages/_arkimet* /usr/lib64/python3.6/site-packages/_dballe* /usr/lib64/python3.6/site-packages/_wreport* /usr/local/lib/python${PYTHON_VERSION}/dist-packages/

COPY --from=arpaesimc /usr/lib/python3.6/site-packages/arkimet /usr/local/lib/python${PYTHON_VERSION}/dist-packages/arkimet/

COPY --from=arpaesimc /usr/lib/python3.6/site-packages/wreport /usr/local/lib/python${PYTHON_VERSION}/dist-packages/wreport/

COPY --from=arpaesimc /usr/lib/python3.6/site-packages/dballe /usr/local/lib/python${PYTHON_VERSION}/dist-packages/dballe/

COPY --from=arpaesimc /usr/lib/python3.6/site-packages/dba_qcfilter /usr/local/lib/python${PYTHON_VERSION}/dist-packages/dba_qcfilter/

COPY --from=arpaesimc /usr/lib/python3.6/site-packages/dba_qcfilter-0.0.2-py3.6.egg-info /usr/local/lib/python${PYTHON_VERSION}/dist-packages/dba_qcfilter-0.0.2-py3.6.egg-info/

# numpy have to be (re)installed here to prevent issues with shared libraries
RUN ln -sf /usr/bin/python${PYTHON_VERSION} /usr/bin/python3.6 && pip3 install --upgrade numpy

WORKDIR /code
