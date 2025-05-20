#!/usr/bin/env python
"""
Script to set the simplified mode configuration in S3.
This allows toggling between full pipeline mode and simplified one-step mode.
"""

import os
import sys
import argparse
from pathlib import Path

# Add parent directory to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from src.config_models import FlowConfig

def main():
    parser = argparse.ArgumentParser(description="Set simplified conversation mode in S3 config")
    parser.add_argument("--enable", action="store_true", help="Enable simplified mode (single prompt)")
    parser.add_argument("--disable", action="store_true", help="Disable simplified mode (use full pipeline)")
    parser.add_argument("--status", action="store_true", help="Show current simplified mode status")
    
    args = parser.parse_args()
    
    # Make sure we have S3 credentials
    bucket_name = os.getenv("FLOW_CONFIG_S3_BUCKET_NAME")
    if not bucket_name:
        print("Error: FLOW_CONFIG_S3_BUCKET_NAME environment variable not set.")
        print("Please set the S3 bucket name before running this script.")
        return 1
    
    # Check current status
    current_config = FlowConfig.get_config_from_s3()
    if current_config is None:
        print("No config found in S3. Creating default config with simplified mode disabled.")
        FlowConfig.init()
        current_config = {"use_simplified_mode": False}  
    
    current_simplified_mode = current_config.get("use_simplified_mode", False)
    
    if args.status or (not args.enable and not args.disable):
        print(f"Current status: simplified_mode is {'ENABLED' if current_simplified_mode else 'DISABLED'}")
        
        if not args.enable and not args.disable:
            print("\nUse --enable or --disable to change the mode.")
            return 0
    
    if args.enable and args.disable:
        print("Error: Cannot specify both --enable and --disable.")
        return 1
    
    # Update the config
    if args.enable and not current_simplified_mode:
        print("Enabling simplified mode...")
        result = FlowConfig.init_simplified()
        print("Simplified mode enabled successfully." if result else "Failed to enable simplified mode.")
    elif args.disable and current_simplified_mode:
        print("Disabling simplified mode...")
        config = FlowConfig(use_simplified_mode=False)
        result = config.init()
        print("Simplified mode disabled successfully." if result else "Failed to disable simplified mode.")
    elif args.enable:
        print("Simplified mode is already enabled.")
    elif args.disable:
        print("Simplified mode is already disabled.")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 