FROM arpaesimc/ubuntu:jammy AS arpaesimc

FROM rapydo/backend:2.4

ARG RAPYDO_VERSION
RUN test -n "$RAPYDO_VERSION"

ARG CURRENT_UID
RUN test -n "$CURRENT_UID"
ENV APIUSER developer

RUN usermod -u $CURRENT_UID $APIUSER

###############################################################################
# DEPENDENCIES
###############################################################################

RUN echo "deb http://security.ubuntu.com/ubuntu jammy-security main" >> /etc/apt/sources.list \
 && apt-get update -qq \
 && apt-get install --yes --no-install-recommends \
      libssl3 \
      libpopt-dev \
      liblzo2-2 \
      libx11-6 \
      libzip4 \
      gdal-bin \
      cmake \
      gfortran \
 && apt-get autoremove --yes \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

ENV DATASET_ROOT="/arkimet/datasets/"

WORKDIR /tmp

###############################################################################
# ECCODES
###############################################################################

ENV ECCODES_VERSION="2.23.0"
ENV ECCODES_DIR="/usr/share/eccodes-build"

# With both definitions from arpaesimc
# ENV ECCODES_DEFINITION_PATH="/usr/share/eccodes-simc/definitions/:/usr/share/eccodes/definitions/"

# Only eccodes-simc from arpaesimc
ENV ECCODES_DEFINITION_PATH="/usr/share/eccodes-simc/definitions/:/usr/share/eccodes-build/share/eccodes/definitions/"

RUN wget --no-check-certificate --quiet "https://confluence.ecmwf.int/download/attachments/45757960/eccodes-${ECCODES_VERSION}-Source.tar.gz?api=v2" -O /tmp/eccodes-${ECCODES_VERSION}-Source.tar.gz \
  && tar -xzf /tmp/eccodes-${ECCODES_VERSION}-Source.tar.gz -C /tmp/ \
  && mkdir /tmp/eccodes-build \
  && cd /tmp/eccodes-build \
  && cmake -DCMAKE_INSTALL_PREFIX=/usr/share/eccodes-build /tmp/eccodes-${ECCODES_VERSION}-Source \
  && make \
  && ctest \
  && make install \
  && ln -sf /usr/share/eccodes-build/lib /usr/share/eccodes-build/lib64 \
  && pip3 install --no-cache-dir eccodes netCDF4 \
  && rm -rf /tmp/eccodes*

################################################################################
## ARPAESIMC
################################################################################

COPY --from=arpaesimc /etc/arkimet /etc/arkimet
COPY --from=arpaesimc /usr/share/eccodes-simc/definitions/ /usr/share/eccodes-simc/definitions/
COPY --from=arpaesimc /usr/share/libsim/ /usr/share/libsim/
COPY --from=arpaesimc /usr/share/wreport/ /usr/share/wreport/

COPY --from=arpaesimc \
    /usr/bin/arki-query \
    /usr/bin/vg6d_transform \
    /usr/bin/v7d_transform \
    /usr/bin/arki-scan \
    /usr/bin/dbadb \
    /usr/bin/dba_qcfilter \
    /usr/bin/

# Split in multiple parts to mitigate preflight timeouts
 COPY --from=arpaesimc \
  /usr/lib/x86_64-linux-gnu/libarkimet.* \
  /usr/lib/x86_64-linux-gnu/libdballe.* \
  /usr/lib/x86_64-linux-gnu/libmeteo-vm2.* \
  /usr/lib/x86_64-linux-gnu/libwreport.* \
  /usr/lib/x86_64-linux-gnu/libeccodes.* \
  /usr/lib/x86_64-linux-gnu/libeccodes_f90.* \
  /usr/lib/x86_64-linux-gnu/libsim_* \
#  /usr/lib/x86_64-linux-gnu/libdballef.* \
  /usr/lib/x86_64-linux-gnu/

COPY --from=arpaesimc \
  /usr/lib/x86_64-linux-gnu/libnetcdff.* \
  /usr/lib/x86_64-linux-gnu/libnetcdf.* \
  /usr/lib/x86_64-linux-gnu/libgeos.* \
  /usr/lib/x86_64-linux-gnu/libgeotiff.* \
  /usr/lib/libgdal.* \
  /usr/lib/x86_64-linux-gnu/libproj.* \
  /usr/lib/x86_64-linux-gnu/libshp.* \
  /usr/lib/x86_64-linux-gnu/

COPY --from=arpaesimc \
  /usr/lib/x86_64-linux-gnu/libgif.* \
  /usr/lib/x86_64-linux-gnu/libopenjp2.* \
  /usr/lib/x86_64-linux-gnu/libjpeg.* \
  /usr/lib/x86_64-linux-gnu/libpng16.* \
  /usr/lib/x86_64-linux-gnu/liblog4c.* \
  /usr/lib/libarmadillo.* \
  /usr/lib/x86_64-linux-gnu/libcfitsio.* \
  /usr/lib/x86_64-linux-gnu/

#COPY --from=arpaesimc \
#  /usr/lib/x86_64-linux-gnu/libfreexl.* \
#  /usr/lib/x86_64-linux-gnu/libodbc.* \
#  /usr/lib/x86_64-linux-gnu/libodbcinst.* \
#  /usr/lib/libogdi.* \
#  /usr/lib/x86_64-linux-gnu/

#COPY --from=arpaesimc \
#  /usr/lib/x86_64-linux-gnu/libpcre.* \
#  /usr/lib/x86_64-linux-gnu/libpoppler.* \
#  /usr/lib/x86_64-linux-gnu/libwebp.* \
#  /usr/lib/x86_64-linux-gnu/libxerces-c-3.2.* \
#  /usr/lib/x86_64-linux-gnu/libsuperlu.* \
#  /usr/lib/x86_64-linux-gnu/liblcms2.* \
#  /usr/lib/x86_64-linux-gnu/libcrypto.* \
#  /usr/lib/x86_64-linux-gnu/libssl.* \
#  /usr/lib/x86_64-linux-gnu/

RUN apt-get install --yes --no-install-recommends \
    libfreexl1 \
    libodbc2 \
    libodbcinst2 \
    libogdi4.1 \
    libpcre2-8-0 \
    libpcre3 \
    libpoppler118 \
    libwebp7 \
    libxerces-c3.2 \
    libsuperlu5 \
    liblcms2-2

COPY --from=arpaesimc \
  /usr/lib/x86_64-linux-gnu/libarchive.so.13* \
  /usr/lib/x86_64-linux-gnu/libxapian.so.30* \
  /usr/lib/x86_64-linux-gnu/libreadline.so.* \
  /usr/lib/x86_64-linux-gnu/

COPY --from=arpaesimc \
  /usr/lib/libmfhdfalt.so.0* \
  /usr/lib/libdfalt.so.0* \
  /usr/lib/

COPY --from=arpaesimc \
  /usr/lib/x86_64-linux-gnu/libhdf5* \
  /usr/lib/x86_64-linux-gnu/libtirpc.so.3* \
  /usr/lib/x86_64-linux-gnu/libpq.so.5* \
  /usr/lib/x86_64-linux-gnu/liblog4fortran.* \
  /usr/lib/x86_64-linux-gnu/libfortrangis.* \
  /usr/lib/x86_64-linux-gnu/libfortranc.* \
  /usr/lib/x86_64-linux-gnu/libgfortran.* \
  /usr/lib/x86_64-linux-gnu/

COPY --from=arpaesimc \
  /usr/lib/x86_64-linux-gnu/liblua5.1.so* \
  /usr/lib/x86_64-linux-gnu/liblapack.* \
  /usr/lib/x86_64-linux-gnu/libarpack.* \
  /usr/lib/x86_64-linux-gnu/libblas.so.3 \
  /usr/lib/x86_64-linux-gnu/

COPY --from=arpaesimc \
  /usr/lib/x86_64-linux-gnu/lapack/liblapack.so.3* \
  /usr/lib/x86_64-linux-gnu/lapack/

COPY --from=arpaesimc \
  /usr/lib/x86_64-linux-gnu/blas/libblas.so.3* \
  /usr/lib/x86_64-linux-gnu/blas/

COPY --from=arpaesimc /usr/lib/python3/dist-packages/_arkimet* /usr/lib/python3/dist-packages/_dballe* /usr/lib/python3/dist-packages/_wreport* /usr/local/lib/python${PYTHON_VERSION}/dist-packages/

COPY --from=arpaesimc /usr/lib/python3/dist-packages/arkimet /usr/local/lib/python${PYTHON_VERSION}/dist-packages/arkimet/

COPY --from=arpaesimc /usr/lib/python3/dist-packages/wreport /usr/local/lib/python${PYTHON_VERSION}/dist-packages/wreport/

COPY --from=arpaesimc /usr/lib/python3/dist-packages/dballe /usr/local/lib/python${PYTHON_VERSION}/dist-packages/dballe/

COPY --from=arpaesimc /usr/lib/python3.10/dist-packages/dba_qcfilter /usr/local/lib/python${PYTHON_VERSION}/dist-packages/dba_qcfilter/

##############################################################################
# NUMPY
# numpy has to be (re)installed here to prevent issues with shared libraries
##############################################################################
RUN pip3 install --upgrade --no-cache-dir numpy

WORKDIR /code
