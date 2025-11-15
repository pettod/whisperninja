from polar_sdk import Polar
from polar_sdk.models.notpermitted import NotPermitted
from polar_sdk.models.resourcenotfound import ResourceNotFound
import json
import os
import httpx
from whisperninja.src.utils.utils import resource_path


def _load_polar_config():
    """Load Polar API configuration from JSON file"""
    config_file = resource_path("whisperninja/config/polar.json")
    default_config = {
        "POLAR_SERVER": "sandbox",
        "POLAR_SANDBOX_ACCESS_TOKEN": "",
        "POLAR_SANDBOX_ORGANIZATION_ID": "",
        "POLAR_PRODUCTION_ACCESS_TOKEN": "",
        "POLAR_PRODUCTION_ORGANIZATION_ID": "",
        "POLAR_LABEL": ""
    }
    
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
                # Merge with defaults to ensure all keys exist
                return {**default_config, **config}
        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"Error loading polar config: {e}")
            return default_config
    return default_config


_polar_config = _load_polar_config()

SERVER = _polar_config.get("POLAR_SERVER", "sandbox")
SANDBOX_ACCESS_TOKEN = _polar_config.get("POLAR_SANDBOX_ACCESS_TOKEN", "")
SANDBOX_ORGANIZATION_ID = _polar_config.get("POLAR_SANDBOX_ORGANIZATION_ID", "")
PRODUCTION_ACCESS_TOKEN = _polar_config.get("POLAR_PRODUCTION_ACCESS_TOKEN", "")
PRODUCTION_ORGANIZATION_ID = _polar_config.get("POLAR_PRODUCTION_ORGANIZATION_ID", "")
LABEL = _polar_config.get("POLAR_LABEL", "")

def get_access_token():
    if SERVER == "sandbox":
        return SANDBOX_ACCESS_TOKEN
    else:
        return PRODUCTION_ACCESS_TOKEN

def get_organization_id():
    if SERVER == "sandbox":
        return SANDBOX_ORGANIZATION_ID
    else:
        return PRODUCTION_ORGANIZATION_ID

def activate_license(license_key):
    access_token = get_access_token()
    organization_id = get_organization_id()
    
    with Polar(
        access_token=access_token,
        server=SERVER
    ) as polar:
        try:
            res = polar.license_keys.activate(request={
                "key": license_key,
                "organization_id": organization_id,
                "label": LABEL,
            })
            print("✅ License activated successfully")
            return True, "License activated successfully"
        except NotPermitted as e:
            message = "License key activation limit already reached"
        except httpx.ConnectError as e:
            message = "No internet connection"
        except httpx.RequestError as e:
            message = "Network request failed"
        except Exception as e:
            message = "Validation failed"
            print(f"Error: {e}")
    print("❌", message)
    return False, message

def validate_license_key(license_key):
    access_token = get_access_token()
    organization_id = get_organization_id()
    
    with Polar(
        access_token=access_token,
        server=SERVER
    ) as polar:
        try:
            res = polar.license_keys.validate(request={
                "key": license_key,
                "organization_id": organization_id,
            })
            print(res)
            print("✅ Valid license key")
            return True, "Valid license key"
        except NotPermitted as e:
            message = "License key validation not permitted"
        except httpx.ConnectError as e:
            message = "No internet connection"
        except httpx.RequestError as e:
            message = "Network request failed"
        except ResourceNotFound as e:
            message = "Invalid license key"
        except Exception as e:
            message = "Validation failed"
            print(f"Error: {e}")
    print("❌", message)
    return False, message
