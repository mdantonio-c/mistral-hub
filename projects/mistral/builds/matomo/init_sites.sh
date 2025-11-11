#!/bin/bash


# Set the auth token (replace with your actual token from Matomo)
auth_token="anonymous"  # Placeholder token; replace with actual token for superuser access
# auth_token=""  # Placeholder token; replace with actual token for superuser access

# Wait for Matomo to be fully initialized
echo "Waiting for Matomo to be ready..."

# Function to check if Matomo is ready
wait_for_matomo() {
    local max_attempts=60
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s http://localhost/index.php | grep -q "Matomo" || curl -s http://localhost/index.php | grep -q "Piwik"; then
            echo "Matomo is responding!"
            return 0
        fi
        echo "Attempt $attempt/$max_attempts: Waiting for Matomo..."
        sleep 5
        attempt=$((attempt + 1))
    done
    
    echo "Matomo did not become ready in time"
    return 1
}

# Function to check if Matomo is installed
check_matomo_installation() {
    local response=$(curl -s http://localhost/index.php)
    if echo "$response" | grep -q "Installation status"; then
        echo "Matomo installation wizard is active - setup required"
        return 1
    elif echo "$response" | grep -q "login" || echo "$response" | grep -q "dashboard"; then
        echo "Matomo is installed and ready"
        return 0
    else
        echo "Unknown Matomo state"
        return 1
    fi
}

# Function to create a site with proper authentication
create_site() {
    local site_name="$1"
    local site_url="$2"
    local auth_token="$3"
    
    echo "Creating site: $site_name"
    echo "Using token: $auth_token"
    
    # Try to create site using the API
    response=$(curl -s -X POST "http://localhost/index.php" \
        -d "module=API&method=SitesManager.addSite" \
        -d "siteName=$site_name" \
        -d "urls=$site_url" \
        -d "format=json" \
        -d "token_auth=$auth_token" 2>/dev/null)
    
    echo "Response for $site_name: $response"
    
    if echo "$response" | grep -q '"value"'; then
        site_id=$(echo "$response" | grep -o '"value":[0-9]*' | cut -d: -f2)
        echo "SUCCESS: Site '$site_name' created with ID: $site_id"
        return 0
    elif echo "$response" | grep -q "superuser"; then
        echo "FAILED: Requires superuser authentication token"
        return 1
    else
        echo "FAILED: API method failed for $site_name"
        return 1
    fi
}

# Wait for Matomo to be ready
if wait_for_matomo; then
    sleep 10

    echo "Checking Matomo installation status..."
    if check_matomo_installation; then
        echo "Matomo is installed, proceeding with site creation..."
        
        # Try to create sites (will likely fail without proper auth token)
        if create_site "MeteoHub-nginx" "https://meteohub.agenziaitaliameteo.it/" "$auth_token"; then
            echo "Site 1 created successfully"
        else
            echo "Site 1 creation failed - auth token required"
        fi
        
        sleep 2

        # if create_site "Website 2" "http://example2.com" "$auth_token"; then
        #     echo "Site 2 created successfully"
        # else
        #     echo "Site 2 creation failed - auth token required"
        # fi
        
        echo ""
        echo "=============================================="
        echo "MANUAL SITE CREATION REQUIRED"
        echo "=============================================="
        echo "API site creation requires superuser authentication."
        echo "Please create sites manually:"
        echo ""
        echo "1. Open http://localhost:8080 in your browser"
        echo "2. Log in with your admin account"
        echo "3. Go to Administration → Websites → Manage"
        echo "4. Click 'Add a new website'"
        echo "5. Create 'Website 1' with URL 'http://example1.com'"
        echo "6. Create 'Website 2' with URL 'http://example2.com'"
        echo ""
        echo "Alternatively, get your API token:"
        echo "1. Go to Administration → Personal → Security"
        echo "2. Copy your 'Auth Token'"
        echo "3. Update this script to use your token instead of 'anonymous'"
        echo "=============================================="
        
        echo "Site creation process completed"
    else
        echo "=============================================="
        echo "MATOMO SETUP REQUIRED"
        echo "=============================================="
        echo "Matomo needs to be set up first."
        echo "Please:"
        echo "1. Open http://localhost:8080 in your browser"
        echo "2. Complete the installation wizard"
        echo "3. After setup, sites can be created via API or manually"
        echo "=============================================="
    fi
else
    echo "Could not connect to Matomo"
fi