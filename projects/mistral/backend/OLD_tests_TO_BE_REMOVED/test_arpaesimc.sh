#!/bin/bash
set -e

echo "Arki-query version: "
arki-query --version

python3 -c "import dballe; print('dballe version', dballe.__version__)"

vg6d_transform --version

v7d_transform --version

arki-scan --help

arki-query --help

dbadb --help

vg6d_transform --help

v7d_transform --help
