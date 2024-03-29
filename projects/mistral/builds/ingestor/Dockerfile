FROM arpaesimc/rockylinux:8 AS arpaesimc

FROM apache/nifi:1.14.0

USER root

ARG CURRENT_UID
RUN test -n "$CURRENT_UID"

ARG CURRENT_GID
RUN test -n "$CURRENT_GID"

RUN usermod -u ${CURRENT_UID} nifi \
    && groupmod -og ${CURRENT_GID} nifi

# This is the version installed on debian 10 with apt-get
ENV PYTHON_VERSION="3.7"

#########################################################
# Dependencies
#########################################################

# Install Python, pip, compilers and dependencies
RUN apt-get update -qq && apt-get install --yes --no-install-recommends python3 python3-dev python3-distutils make gcc g++ cmake gfortran gdal-bin libgdal-dev \
    && apt-get autoremove --yes \
    && apt-get clean \
    && curl --silent https://bootstrap.pypa.io/get-pip.py --output get-pip.py \
    && python3 get-pip.py \
    && rm get-pip.py \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Arkimet and other binary explicitly use python3.6 interpreter
# Let's override to force them to use py37
RUN ln -sf /usr/bin/python${PYTHON_VERSION} /usr/bin/python3.6

WORKDIR /tmp

#########################################################
# ECCODES
#########################################################

ENV ECCODES_VERSION="2.23.0"
ENV ECCODES_DIR="/usr/share/eccodes-build"

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

#########################################################
# GDAL
#########################################################

ENV LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH

RUN pip3 install --no-cache-dir numpy setuptools==57.5.0 \
    && pip3 install --no-cache-dir GDAL==$(gdal-config --version) --global-option=build_ext --global-option="-I/usr/include/gdal"

#########################################################
# arpaesimc
#########################################################

COPY --from=arpaesimc /usr/bin /usr/bin/centos

# Copied from Backend. VERY IMPORTANT: removed /usr/lib64/libproj.*
COPY --from=arpaesimc /usr/lib64/libarkimet.* /usr/lib64/libdballe.* /usr/lib64/libmeteo-vm2.* /usr/lib64/libwreport.* /usr/lib64/libeccodes.* /usr/lib64/libeccodes_f90.* /usr/lib64/libsim_* /usr/lib64/libdballef.* /usr/lib64/libnetcdff.* /usr/lib64/libnetcdf.* /usr/lib64/liblog4fortran.* /usr/lib64/libfortrangis.* /usr/lib64/libfortranc.* /usr/lib64/libgfortran.* /usr/lib64/libgdal.* /usr/lib64/libshp.* /usr/lib64/liblog4c.* /usr/lib64/libarmadillo.* /usr/lib64/libcfitsio.* /usr/lib64/libdap.so.* /usr/lib64/libdapclient.* /usr/lib64/libdapserver.* /usr/lib64/libfreexl.* /usr/lib64/libgeos-3.7.2.* /usr/lib64/libgeotiff.* /usr/lib64/libgif.* /usr/lib64/libgta.* /usr/lib64/libodbc.* /usr/lib64/libodbcinst.* /usr/lib64/libogdi.* /usr/lib64/libopenjp2.* /usr/lib64/libpcre.* /usr/lib64/libpoppler.* /usr/lib64/libwebp.* /usr/lib64/libxerces-c-3.2.* /usr/lib64/libsuperlu.* /usr/lib64/liblcms2.* /usr/lib64/libcrypto.* /usr/lib64/libssl.* /usr/lib64/libjpeg.* /usr/lib64/libpng16.* /usr/lib64/libarchive.so.13* /usr/lib64/libmariadb.so.3* /usr/lib64/libxapian.so.30* /usr/lib64/liblua-5.3.so* /usr/lib64/libreadline.so.7* /usr/lib64/libjasper.so.4* /usr/lib64/libmfhdf.so.0* /usr/lib64/libdf.so.0* /usr/lib64/libhdf5_hl.so.100* /usr/lib64/libhdf5.so.103* /usr/lib64/libtirpc.so.3* /usr/lib64/libopenblasp.so.0* /usr/lib64/libpq.so.5* /usr/lib64/libopenblaso.* /usr/lib64/liblapack.* /usr/lib64/libarpack.* /usr/lib64/libblas.* /usr/lib64/atlas /usr/lib/x86_64-linux-gnu/

COPY --from=arpaesimc /usr/lib64/libpython3.6m.so* /usr/lib/x86_64-linux-gnu/
# Additional shared libraries (not explicity needed on backend because already available or installed via apt)
COPY --from=arpaesimc /usr/lib64/libzip.so.5* /usr/lib64/liblzo2.so.2* /usr/lib64/libeccodes.so.0.1* /usr/lib64/libpopt.so.0* usr/lib64/libaec.so.0* /usr/lib64/libgomp.so.1* /usr/lib/x86_64-linux-gnu/

COPY --from=arpaesimc /etc/arkimet /etc/arkimet

COPY --from=arpaesimc /usr/share/eccodes-simc/definitions/ /usr/share/eccodes-simc/definitions/
COPY --from=arpaesimc /usr/share/libsim/ /usr/share/libsim/
COPY --from=arpaesimc /usr/share/wreport/ /usr/share/wreport/

COPY --from=arpaesimc /usr/lib64/python3.6/site-packages/_arkimet* /usr/lib64/python3.6/site-packages/_dballe* usr/lib64/python3.6/site-packages/_wreport* /usr/local/lib/python${PYTHON_VERSION}/dist-packages/
RUN mv /usr/local/lib/python${PYTHON_VERSION}/dist-packages/_wreport.cpython-36m-x86_64-linux-gnu.so /usr/local/lib/python3.7/dist-packages/_wreport.so

COPY --from=arpaesimc /usr/lib/python3.6/site-packages/arkimet /usr/local/lib/python${PYTHON_VERSION}/dist-packages/arkimet/

COPY --from=arpaesimc /usr/lib64/python3.6/site-packages/wreport /usr/local/lib/python${PYTHON_VERSION}/dist-packages/wreport/

COPY --from=arpaesimc /usr/lib/python3.6/site-packages/dballe /usr/local/lib/python${PYTHON_VERSION}/dist-packages/dballe/

COPY --from=arpaesimc /usr/lib/python3.6/site-packages/dba_qcfilter /usr/local/lib/python${PYTHON_VERSION}/dist-packages/dba_qcfilter/

COPY --from=arpaesimc /usr/lib/python3.6/site-packages/dba_qcfilter-0.0.3-py3.6.egg-info /usr/local/lib/python${PYTHON_VERSION}/dist-packages/dba_qcfilter-0.0.3-py3.6.egg-info/

#########################################################
# NIFI
#########################################################

# Create working directories
RUN mkdir -p /opt/nifi/nifi_ok_flowfile \
    /opt/nifi/nifi_error_flowfile \
    /opt/nifi/temp

RUN chown -R nifi:nifi /opt/nifi


# Install database drivers
RUN mkdir /home/nifi/nifi-driver && \
    wget --quiet -O /home/nifi/nifi-driver/postgresql-42.2.19.jar https://jdbc.postgresql.org/download/postgresql-42.2.19.jar && \
    chown -R nifi:nifi /home/nifi/nifi-driver

RUN cp -r ${NIFI_HOME}/conf ${NIFI_HOME}/default-conf && chown -R nifi:nifi ${NIFI_HOME}/default-conf

COPY --chmod=700 docker-entrypoint.sh /usr/local/bin/docker-entrypoint

WORKDIR ${NIFI_HOME}
ENV PATH="$PATH:/usr/bin/centos"
# RCE su log4j CVE-2021-44228
ENV JAVA_OPTS="${JAVA_OPTS} -Dlog4j2.formatMsgNoLookups=true"

ENTRYPOINT ["/usr/local/bin/docker-entrypoint"]
