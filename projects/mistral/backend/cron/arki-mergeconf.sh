#!/bin/bash

# This script is actually unused

set -a

source /etc/rapydo-environment

# List non empty datasets (i.e. folders containing a config file)
# otherwise arki-mergeconf will fail with:
# RuntimeError: cannot open file /arkimet/datasets/cosmo_2Ipp_ecPoint/config: No such file or directory
DATASETS=$(find /arkimet/datasets/*/ -type f -name 'config' | sed -r 's|/[^/]+$||' | tr '\n' ' ')

/usr/bin/centos/arki-mergeconf --extra $DATASETS > /arkimet/config/arkimet.conf.tmp

/bin/mv /arkimet/config/arkimet.conf.tmp /arkimet/config/arkimet.conf
