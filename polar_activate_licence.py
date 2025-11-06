from polar_sdk import Polar
from polar_sdk.models.notpermitted import NotPermitted
from dotenv import load_dotenv
import os
import httpx

load_dotenv()

LICENSE_KEY = "226EF247-D672-437F-8DF0-27A7CE469B93"
SERVER = os.getenv("POLAR_SERVER")
SANDBOX_ACCESS_TOKEN = os.getenv("POLAR_SANDBOX_ACCESS_TOKEN")
SANDBOX_ORGANIZATION_ID = os.getenv("POLAR_SANDBOX_ORGANIZATION_ID")
PRODUCTION_ACCESS_TOKEN = os.getenv("POLAR_PRODUCTION_ACCESS_TOKEN")
PRODUCTION_ORGANIZATION_ID = os.getenv("POLAR_PRODUCTION_ORGANIZATION_ID")
LABEL = os.getenv("POLAR_LABEL")


def activate_license(access_token, license_key, organization_id, server, label):
    with Polar(
        access_token=access_token,
        server=server
    ) as polar:
        try:
            res = polar.license_keys.activate(request={
                "key": license_key,
                "organization_id": organization_id,
                "label": label,
            })
            return True
        except NotPermitted as e:
            print("❌ License key activation limit already reached")
        except httpx.ConnectError as e:
            print("❌ No internet connection")
        except httpx.RequestError as e:
            print("❌ Network request failed")
    return False


def validate_license(access_token, license_key, organization_id, server):
    with Polar(
        access_token=access_token,
        server=server
    ) as polar:
        try:
            res = polar.license_keys.validate(request={
                "key": license_key,
                "organization_id": organization_id,
            })
            print(res)
            return True
        except NotPermitted as e:
            print("❌ License key validation not permitted")
        except httpx.ConnectError as e:
            print("❌ No internet connection")
        except httpx.RequestError as e:
            print("❌ Network request failed")
        except Exception as e:
            print("❌ Validation failed")
            print(f"Error: {e}")
    return False


def main():
    if SERVER == "sandbox":
        ACCESS_TOKEN = SANDBOX_ACCESS_TOKEN
        ORGANIZATION_ID = SANDBOX_ORGANIZATION_ID
    else:
        ACCESS_TOKEN = PRODUCTION_ACCESS_TOKEN
        ORGANIZATION_ID = PRODUCTION_ORGANIZATION_ID
    if activate_license(ACCESS_TOKEN, LICENSE_KEY, ORGANIZATION_ID, SERVER, LABEL):
        print("✅ License key activated successfully")
    else:
        print("❌ License key activation failed")
    if validate_license(ACCESS_TOKEN, LICENSE_KEY, ORGANIZATION_ID, SERVER):
        print("✅ License key validated successfully")
    else:
        print("❌ License key validation failed")

if __name__ == "__main__":
    main()