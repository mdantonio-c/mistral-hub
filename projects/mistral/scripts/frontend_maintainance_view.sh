#!/bin/bash

# Usage function
show_help() {
    echo "Usage: $0 enable|disable [--app|--ui|--all]"
    echo "  -h       - Show this help message"
    echo "  enable   - Enable maintenance view (for APP and UI by default)"
    echo "  disable  - Disable maintenance view for all routes"
    echo "  --app    - Apply to application only (optional)"
    echo "  --ui     - Apply to UI only (optional)"
    echo "  --all    - Apply to ALL routes"
}

# Check arguments
if [[ $# -ne 1 && $# -ne 2 ]]; then
    show_help
    exit 1
fi

case "$1" in
    enable)
        # Replace with your actual command to enable maintenance
        echo "Enabling maintenance view..."
        case "$2" in
            --app)
                rapydo shell proxy "./toggle_maintenance.sh enable --app"
                ;;
            --ui)
                rapydo shell proxy "./toggle_maintenance.sh enable --ui"
                ;;
            --all)
                rapydo shell proxy "./toggle_maintenance.sh enable --all"
                ;;
            "" )
                rapydo shell proxy "./toggle_maintenance.sh enable"
                ;;
            * )
                echo "Unknown option: $2"
                show_help
                exit 1
                ;;
        esac
        ;;
    disable)
        # Replace with your actual command to disable maintenance
        echo "Disabling maintenance view..."
        rapydo shell proxy "./toggle_maintenance.sh disable"
        ;;
    *)
        show_help
        exit 1
        ;;
esac