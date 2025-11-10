#!/bin/bash

# Script to create sites after Matomo is fully set up
echo "Creating sites in Matomo..."

# Function to create a site using API with proper authentication
create_site_with_auth() {
    local site_name="$1"
    local site_url="$2"
    local token_auth="$3"
    
    echo "Creating site: $site_name with URL: $site_url"
    
    if [ -z "$token_auth" ] || [ "$token_auth" = "anonymous" ]; then
        echo "Warning: Using anonymous token, this may not work for site creation"
    fi
    
    # Try to create site using the API
    response=$(curl -s -X POST "http://localhost/index.php" \
        -d "module=API&method=SitesManager.addSite" \
        -d "siteName=$site_name" \
        -d "urls=$site_url" \
        -d "format=json" \
        -d "token_auth=$token_auth" 2>/dev/null)
    
    echo "API Response: $response"
    
    if echo "$response" | grep -q '"value"'; then
        site_id=$(echo "$response" | grep -o '"value":[0-9]*' | cut -d: -f2)
        echo "SUCCESS: Site '$site_name' created with ID: $site_id"
        return 0
    else
        echo "FAILED: Could not create site '$site_name'"
        return 1
    fi
}

# Function to try creating sites with different approaches
create_sites() {
    echo "Attempting to create 2 sites..."
    
    # You'll need to replace 'anonymous' with actual auth token after setup
    # The token can be found in Matomo -> Administration -> Personal -> Security
    local auth_token="7843e0014a66ad2c193e098e26537141"
    
    echo "NOTE: Using anonymous token - this will likely fail"
    echo "To fix this:"
    echo "1. Log into Matomo at http://localhost:8080"
    echo "2. Go to Administration → Personal → Security"
    echo "3. Copy your 'Auth Token'"
    echo "4. Replace 'anonymous' in this script with your actual token"
    echo ""
    
    create_site_with_auth "Website 1" "http://example1.com" "$auth_token"
    sleep 1
    create_site_with_auth "Website 2" "http://example2.com" "$auth_token"
    
    echo "Site creation attempts completed."
    echo ""
    echo "If sites were not created successfully:"
    echo "1. Get your auth token from Matomo -> Administration -> API"
    echo "2. Replace 'anonymous' in this script with your actual token"
    echo "3. Or create sites manually in Matomo -> Administration -> Websites -> Manage"
}

# Check if Matomo is responding
if curl -s http://localhost/index.php > /dev/null; then
    create_sites
else
    echo "Cannot connect to Matomo. Make sure it's running and accessible."
fi