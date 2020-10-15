FROM arpaesimc/centos:8 AS arpaesimc

FROM rapydo/backend:0.8

ARG CURRENT_UID
RUN test -n "$CURRENT_UID"
ENV APIUSER developer

RUN usermod -u $CURRENT_UID $APIUSER

RUN apt-get update \
 && apt-get install --yes software-properties-common \
 && add-apt-repository "deb http://security.ubuntu.com/ubuntu xenial-security main" \
 && pip3 install --use-feature=2020-resolver eccodes-python \
 && apt-get install --yes \
      libpq-dev \
      libssl1.0.0 \
      libssl-dev \
      libpopt-dev \
      liblzo2-2 \
      libx11-6 \
      libzip5 \
      gdal-bin \
      python3-eccodes \
 && apt-get autoremove --yes \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/* \
 && python3 -m eccodes selfcheck

ENV LD_LIBRARY_PATH="$LD_LIBRARY_PATH:/usr/lib/x86_64-linux-gnu/hdf5/serial"
ENV PATH="$PATH:/usr/bin/centos"
ENV ECCODES_DEFINITION_PATH="/usr/share/eccodes-simc/definitions/:/usr/share/eccodes/definitions/"
ENV DATASET_ROOT="/arkimet/datasets/"

WORKDIR /usr/lib/x86_64-linux-gnu/hdf5/serial

WORKDIR /usr/lib/x86_64-linux-gnu

RUN ln -s libreadline.so libreadline.so.6

COPY --from=arpaesimc /usr/bin /usr/bin/centos

COPY --from=arpaesimc /etc/arkimet /etc/arkimet
COPY --from=arpaesimc /usr/share/eccodes /usr/share/
COPY --from=arpaesimc /usr/share/eccodes-simc/definitions/ /usr/share/eccodes-simc/definitions/
COPY --from=arpaesimc /usr/share/eccodes/definitions/ /usr/share/eccodes/definitions/
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

COPY --from=arpaesimc /usr/lib64/libarkimet.* /usr/lib64/libdballe.* /usr/lib64/libmeteo-vm2.* /usr/lib64/libwreport.* /usr/lib64/libeccodes.* /usr/lib64/libeccodes_f90.* /usr/lib64/libsim_* /usr/lib64/libdballef.* /usr/lib64/libnetcdff.* /usr/lib64/libnetcdf.* /usr/lib64/liblog4fortran.* /usr/lib64/libfortrangis.* /usr/lib64/libfortranc.* /usr/lib64/libgfortran.* /usr/lib64/libgdal.* /usr/lib64/libproj.* /usr/lib64/libshp.* /usr/lib64/liblog4c.* /usr/lib64/libarmadillo.* /usr/lib64/libcfitsio.* /usr/lib64/libdap.so.* /usr/lib64/libdapclient.* /usr/lib64/libdapserver.* /usr/lib64/libfreexl.* /usr/lib64/libgeos-3.7.2.* /usr/lib64/libgeotiff.* /usr/lib64/libgif.* /usr/lib64/libgta.* /usr/lib64/libodbc.* /usr/lib64/libodbcinst.* /usr/lib64/libogdi.* /usr/lib64/libopenjp2.* /usr/lib64/libpcre.* /usr/lib64/libpoppler.* /usr/lib64/libwebp.* /usr/lib64/libxerces-c-3.2.* /usr/lib64/libopenblaso.* /usr/lib64/liblapack.* /usr/lib64/libarpack.* /usr/lib64/libsuperlu.* /usr/lib64/liblcms2.* /usr/lib64/libcrypto.* /usr/lib64/libssl.* /usr/lib64/libblas.* /usr/lib64/atlas /usr/lib64/libjpeg.* /usr/lib64/libpng16.* /usr/lib64/libarchive.so.13* /usr/lib64/libmariadb.so.3* /usr/lib64/libxapian.so.30* /usr/lib64/liblua-5.3.so* /usr/lib64/libreadline.so.7* /usr/lib64/libjasper.so.4* /usr/lib64/libmfhdf.so.0* /usr/lib64/libdf.so.0* /usr/lib64/libhdf5_hl.so.100* /usr/lib64/libhdf5.so.103* /usr/lib64/libtirpc.so.3* /lib/x86_64-linux-gnu/

COPY --from=arpaesimc /usr/lib64/python3.6/site-packages/_arkimet* /usr/lib64/python3.6/site-packages/_dballe* /usr/lib64/python3.6/site-packages/_wreport* /usr/local/lib/python3.8/dist-packages/

COPY --from=arpaesimc /usr/lib/python3.6/site-packages/arkimet /usr/local/lib/python3.8/dist-packages/arkimet/

COPY --from=arpaesimc /usr/lib/python3.6/site-packages/wreport /usr/local/lib/python3.8/dist-packages/wreport/

COPY --from=arpaesimc /usr/lib/python3.6/site-packages/dballe /usr/local/lib/python3.8/dist-packages/dballe/

COPY --from=arpaesimc /usr/lib/python3.6/site-packages/dba_qcfilter /usr/local/lib/python3.8/dist-packages/dba_qcfilter/

COPY --from=arpaesimc /usr/lib/python3.6/site-packages/dba_qcfilter-0.0.2-py3.6.egg-info /usr/local/lib/python3.8/dist-packages/dba_qcfilter-0.0.2-py3.6.egg-info/

RUN ln -sf /usr/bin/python3.8 /usr/bin/python3.6

WORKDIR /code
