#!/usr/bin/env python3
"""
Example demonstrating how to use the ZSCALER_USE_LEGACY environment variable.

This example shows how to configure the MCP server to use legacy APIs
via environment variable instead of specifying use_legacy in every tool call.
"""

import os
from zscaler_mcp.client import get_zscaler_client


def example_oneapi_mode():
    """Example using OneAPI mode (default)."""
    print("=== OneAPI Mode Example ===")
    
    # Set environment variables for OneAPI
    os.environ.update({
        'ZSCALER_CLIENT_ID': 'your_client_id',
        'ZSCALER_CLIENT_SECRET': 'your_client_secret', 
        'ZSCALER_CUSTOMER_ID': 'your_customer_id',
        'ZSCALER_VANITY_DOMAIN': 'your_vanity_domain',
        'ZSCALER_CLOUD': 'beta',
        'ZSCALER_USE_LEGACY': 'false'  # Explicitly set to false (default)
    })
    
    try:
        # This will use OneAPI mode
        client = get_zscaler_client()
        print("✅ Successfully created OneAPI client")
        print(f"Client type: {type(client).__name__}")
    except Exception as e:
        print(f"❌ Error: {e}")


def example_legacy_zpa_mode():
    """Example using Legacy ZPA mode via environment variable."""
    print("\n=== Legacy ZPA Mode Example ===")
    
    # Set environment variables for Legacy ZPA
    os.environ.update({
        'ZPA_CLIENT_ID': 'your_zpa_client_id',
        'ZPA_CLIENT_SECRET': 'your_zpa_client_secret',
        'ZPA_CUSTOMER_ID': 'your_zpa_customer_id', 
        'ZPA_CLOUD': 'beta',
        'ZSCALER_USE_LEGACY': 'true'  # Enable legacy mode
    })
    
    try:
        # This will use Legacy ZPA mode
        client = get_zscaler_client(service='zpa')
        print("✅ Successfully created Legacy ZPA client")
        print(f"Client type: {type(client).__name__}")
    except Exception as e:
        print(f"❌ Error: {e}")


def example_legacy_zia_mode():
    """Example using Legacy ZIA mode via environment variable."""
    print("\n=== Legacy ZIA Mode Example ===")
    
    # Set environment variables for Legacy ZIA
    os.environ.update({
        'ZIA_USERNAME': 'your_zia_username',
        'ZIA_PASSWORD': 'your_zia_password',
        'ZIA_API_KEY': 'your_zia_api_key',
        'ZIA_CLOUD': 'beta',
        'ZSCALER_USE_LEGACY': 'true'  # Enable legacy mode
    })
    
    try:
        # This will use Legacy ZIA mode
        client = get_zscaler_client(service='zia')
        print("✅ Successfully created Legacy ZIA client")
        print(f"Client type: {type(client).__name__}")
    except Exception as e:
        print(f"❌ Error: {e}")


def example_legacy_zcc_mode():
    """Example using Legacy ZCC mode via environment variable."""
    print("\n=== Legacy ZCC Mode Example ===")
    
    # Set environment variables for Legacy ZCC
    os.environ.update({
        'ZCC_CLIENT_ID': 'your_zcc_client_id',
        'ZCC_CLIENT_SECRET': 'your_zcc_client_secret',
        'ZCC_CLOUD': 'beta',
        'ZSCALER_USE_LEGACY': 'true'  # Enable legacy mode
    })
    
    try:
        # This will use Legacy ZCC mode
        client = get_zscaler_client(service='zcc')
        print("✅ Successfully created Legacy ZCC client")
        print(f"Client type: {type(client).__name__}")
    except Exception as e:
        print(f"❌ Error: {e}")


def example_legacy_zdx_mode():
    """Example using Legacy ZDX mode via environment variable."""
    print("\n=== Legacy ZDX Mode Example ===")
    
    # Set environment variables for Legacy ZDX
    os.environ.update({
        'ZDX_CLIENT_ID': 'your_zdx_client_id',
        'ZDX_CLIENT_SECRET': 'your_zdx_client_secret',
        'ZDX_CLOUD': 'beta',
        'ZSCALER_USE_LEGACY': 'true'  # Enable legacy mode
    })
    
    try:
        # This will use Legacy ZDX mode
        client = get_zscaler_client(service='zdx')
        print("✅ Successfully created Legacy ZDX client")
        print(f"Client type: {type(client).__name__}")
    except Exception as e:
        print(f"❌ Error: {e}")


def example_parameter_override():
    """Example showing how parameter overrides environment variable."""
    print("\n=== Parameter Override Example ===")
    
    # Set environment variable to legacy mode
    os.environ.update({
        'ZSCALER_USE_LEGACY': 'true',
        'ZSCALER_CLIENT_ID': 'your_client_id',
        'ZSCALER_CLIENT_SECRET': 'your_client_secret',
        'ZSCALER_CUSTOMER_ID': 'your_customer_id',
        'ZSCALER_VANITY_DOMAIN': 'your_vanity_domain',
        'ZSCALER_CLOUD': 'beta'
    })
    
    try:
        # Explicitly override to OneAPI mode
        client = get_zscaler_client(use_legacy=False)
        print("✅ Successfully created OneAPI client (parameter override)")
        print(f"Client type: {type(client).__name__}")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    print("ZSCALER_USE_LEGACY Environment Variable Examples")
    print("=" * 50)
    
    # Note: These examples will fail with real credentials
    # but demonstrate the configuration patterns
    
    example_oneapi_mode()
    example_legacy_zpa_mode() 
    example_legacy_zia_mode()
    example_legacy_zcc_mode()
    example_legacy_zdx_mode()
    example_parameter_override()
    
    print("\n" + "=" * 50)
    print("Configuration Summary:")
    print("- Set ZSCALER_USE_LEGACY=true to enable legacy mode for all tools")
    print("- Set ZSCALER_USE_LEGACY=false or omit to use OneAPI mode (default)")
    print("- Parameter use_legacy can override environment variable")
    print("- Legacy mode requires service parameter and appropriate credentials") 