#!/bin/bash

FLAG_PATH="/etc/nginx/maintenance.flag"
NGINX_CONF_DIR="/etc/nginx/sites-enabled"
TEMPLATE_CONF="sites-enabled-templates/custom_maintenance.conf"
PROD_CONF="$NGINX_CONF_DIR/production.conf"
DISABLED_CONF="$NGINX_CONF_DIR/production.conf.disabled"
MAINT_CONF="$NGINX_CONF_DIR/custom_maintenance.conf"

enable_maintenance() {
    case "$1" in
        --app)
            echo "🔧 Enabling maintenance mode for APP..."
            touch "$FLAG_PATH.app"
            ;;
        --ui)
            echo "🔧 Enabling maintenance mode for UI..."
            touch "$FLAG_PATH.ui"
            ;;
        --all)
            echo "🔧 Enabling maintenance mode for ALL routes..."
            touch "$FLAG_PATH" "$FLAG_PATH.app" "$FLAG_PATH.ui"

            if [ -f "$PROD_CONF" ]; then
                mv "$PROD_CONF" "$DISABLED_CONF"
            fi

            cp "$TEMPLATE_CONF" "$MAINT_CONF"
            ;;
        "")
            echo "🔧 Enabling maintenance mode for APP and UI..."
            touch "$FLAG_PATH.app" "$FLAG_PATH.ui"
            ;;
        *)
            echo "❌ Unknown option: $1"
            echo "Usage: $0 enable|disable [--app|--ui|--all]"
            exit 1
            ;;
    esac

    echo "🔍 Testing NGINX configuration..."
    if nginx -t; then
        echo "✅ Reloading NGINX..."
        nginx -s reload
    else
        echo "❌ NGINX config test failed. Please check your configuration."
        exit 1
    fi
}

disable_maintenance() {
    echo "🔧 Disabling maintenance mode..."
    rm -f "$FLAG_PATH" "$FLAG_PATH.app" "$FLAG_PATH.ui"

    if [ -f "$MAINT_CONF" ]; then
        rm -f "$MAINT_CONF"
    fi

    if [ -f "$DISABLED_CONF" ]; then
        mv "$DISABLED_CONF" "$PROD_CONF"
    fi

    echo "🔍 Testing NGINX configuration..."
    if nginx -t; then
        echo "✅ Reloading NGINX..."
        nginx -s reload
    else
        echo "❌ NGINX config test failed. Please check your configuration."
        exit 1
    fi
}

# Entry point
case "$1" in
    enable)
        enable_maintenance "$2"
        ;;
    disable)
        disable_maintenance
        ;;
    *)
        echo "Usage: $0 enable|disable [--app|--ui|--all]"
        exit 1
        ;;
esac
