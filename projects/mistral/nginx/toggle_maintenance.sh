#!/bin/bash

FLAG_PATH="/etc/nginx/maintenance.flag"

enable_maintenance() {
    case "$1" in
        --app)
            echo "Maintenance mode enabled for app."
            touch "$FLAG_PATH".app
            ;;
        --ui)
            echo "Maintenance mode enabled for UI."
            touch "$FLAG_PATH".ui
            ;;
        "")
            echo "Maintenance mode enabled for both app and UI."
            touch "$FLAG_PATH".app
            touch "$FLAG_PATH".ui
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 enable|disable [--app|--ui]"
            exit 1
            ;;
    esac
    nginx -s reload
}

disable_maintenance() {
    rm -f "$FLAG_PATH".app
    rm -f "$FLAG_PATH".ui
    echo "Maintenance mode disabled."
    nginx -s reload
}

if [ "$1" == "enable" ]; then
    enable_maintenance "$2"
elif [ "$1" == "disable" ]; then
    disable_maintenance
else
    echo "Usage: $0 enable|disable [--app|--ui]"
    exit 1
fi