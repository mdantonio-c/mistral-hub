#!/usr/bin/env python3
import requests
import time
import sys
import json

def wait_for_matomo(url, max_retries=30):
    """Wait for Matomo to be ready"""
    for i in range(max_retries):
        try:
            response = requests.get(f"{url}/index.php", timeout=10)
            if response.status_code == 200:
                print("Matomo is ready!")
                return True
        except requests.exceptions.RequestException:
            pass
        
        print(f"Waiting for Matomo... ({i+1}/{max_retries})")
        time.sleep(10)
    
    return False

def setup_matomo(url):
    """Setup Matomo with initial configuration"""
    print("Setting up Matomo...")
    
    # First, let's try to get the installation status
    try:
        response = requests.get(f"{url}/index.php?module=Installation", timeout=10)
        if "Installation" in response.text or "Welcome to Matomo" in response.text:
            print("Matomo needs initial setup...")
            # This would require interactive setup through the web interface
            # For now, we'll assume Matomo is already set up
    except Exception as e:
        print(f"Error checking Matomo status: {e}")

def create_site(url, site_name, site_url, token_auth="anonymous"):
    """Create a site in Matomo"""
    print(f"Creating site: {site_name}")
    
    data = {
        'module': 'API',
        'method': 'SitesManager.addSite',
        'siteName': site_name,
        'urls': site_url,
        'format': 'json',
        'token_auth': token_auth
    }
    
    try:
        response = requests.post(f"{url}/index.php", data=data, timeout=30)
        print(f"Response status: {response.status_code}")
        print(f"Response text: {response.text}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                if 'value' in result:
                    print(f"Site '{site_name}' created with ID: {result['value']}")
                    return result['value']
                else:
                    print(f"Unexpected response format: {result}")
            except json.JSONDecodeError:
                print(f"Non-JSON response: {response.text}")
        else:
            print(f"Failed to create site. Status: {response.status_code}")
    
    except Exception as e:
        print(f"Error creating site '{site_name}': {e}")
    
    return None

def main():
    matomo_url = "http://matomo:80"
    
    # Wait for Matomo to be ready
    if not wait_for_matomo(matomo_url):
        print("Matomo did not become ready in time")
        sys.exit(1)
    
    # Give Matomo a bit more time to fully initialize
    time.sleep(10)
    
    # Try to create sites
    sites = [
        ("Website 1", "http://example1.com"),
        ("Website 2", "http://example2.com")
    ]
    
    for site_name, site_url in sites:
        create_site(matomo_url, site_name, site_url)
        time.sleep(2)  # Small delay between creations

if __name__ == "__main__":
    main()