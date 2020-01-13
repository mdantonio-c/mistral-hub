#!/bin/sh


echo "project_configuration:" >> .projectrc
echo "  variables:" >> .projectrc
echo "    env:" >> .projectrc
echo "      CELERYUI_PASSWORD: test${RANDOM}" >> .projectrc
echo "      CELERYUI_USER: test${RANDOM}" >> .projectrc
echo "      RABBITMQ_USER: test${RANDOM}" >> .projectrc
echo "      RABBITMQ_PASSWORD: test${RANDOM}" >> .projectrc


