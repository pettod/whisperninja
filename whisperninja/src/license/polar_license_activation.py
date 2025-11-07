from polar_sdk import Polar
from polar_sdk.models.notpermitted import NotPermitted
from polar_sdk.models.resourcenotfound import ResourceNotFound
from dotenv import load_dotenv
import os
import httpx


load_dotenv()

SERVER = os.getenv("POLAR_SERVER")
SANDBOX_ACCESS_TOKEN = os.getenv("POLAR_SANDBOX_ACCESS_TOKEN")
SANDBOX_ORGANIZATION_ID = os.getenv("POLAR_SANDBOX_ORGANIZATION_ID")
PRODUCTION_ACCESS_TOKEN = os.getenv("POLAR_PRODUCTION_ACCESS_TOKEN")
PRODUCTION_ORGANIZATION_ID = os.getenv("POLAR_PRODUCTION_ORGANIZATION_ID")
LABEL = os.getenv("POLAR_LABEL")

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
