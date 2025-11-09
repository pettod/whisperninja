import os
from datetime import datetime
from whisperninja.src.utils.utils import resource_path
from whisperninja.src.license.polar_license_activation import activate_license, validate_license_key
from whisperninja.src.license.license_storage import (
    LicenseEncryptionError,
    read_license_data,
    write_license_data,
)


class LicenseManager:
    """Singleton class for managing license data from JSON file"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls, license_file="whisperninja/config/license.json"):
        """Singleton pattern - only create one instance"""
        if cls._instance is None:
            cls._instance = super(LicenseManager, cls).__new__(cls)
        return cls._instance
    
    @classmethod
    def instance(cls):
        """Get the singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self, license_file="whisperninja/config/license.json"):
        """Initialize the license manager (only runs once due to singleton)"""
        if LicenseManager._initialized:
            return
        
        self.license_file = resource_path(license_file)
        self.license_data = self.load_license()
        
        # Cache the license activation status in memory (no file read needed)
        self._is_license_active = self.license_data.get("is_license_activated", False)
        
        LicenseManager._initialized = True
    
    def load_license(self):
        """Load license data from JSON file"""
        if os.path.exists(self.license_file):
            try:
                data = read_license_data(self.license_file)
                if isinstance(data, dict) and data:
                    return data
            except LicenseEncryptionError as exc:
                print(f"Error decrypting license: {exc}")
            except Exception as exc:
                print(f"Unexpected error loading license: {exc}")
        return self._get_default_license_data()
    
    def _get_default_license_data(self):
        """Get default license data structure"""
        return {
            "is_license_activated": False,
            "license_key": "",
            "max_trial_days": 7,
            "installation_timestamp": None
        }
    
    def save_license(self):
        """Save license data to JSON file"""
        try:
            write_license_data(self.license_data, self.license_file)
            return True
        except Exception as e:
            print(f"Error saving license: {e}")
            return False

    def is_installation_complete(self):
        """Return True when initial installation/setup has been completed."""
        installation_timestamp = self.license_data.get("installation_timestamp")
        return bool(installation_timestamp)

    def mark_installation_complete(self):
        """Stamp the installation as complete by recording the current timestamp."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        current = self.license_data.get("installation_timestamp")
        if current:
            return current

        self.license_data["installation_timestamp"] = timestamp
        self.save_license()
        return timestamp
    
    def is_license_active(self):
        """Get whether the license is activated (cached in memory, no file read)"""
        return self._is_license_active
    
    def get_trial_days_left(self):
        """Calculate the number of trial days left (no file read, just datetime math)"""
        installation_timestamp = self.license_data.get("installation_timestamp")
        if not installation_timestamp:
            return self.license_data.get("max_trial_days", 7)
        
        try:
            installation_datetime = datetime.strptime(installation_timestamp, "%Y-%m-%d %H:%M:%S")
            today = datetime.now()
            days_elapsed = (today - installation_datetime).days
            days_left = self.license_data.get("max_trial_days", 7) - days_elapsed
            return max(0, days_left)  # Don't return negative days
        except (ValueError, TypeError) as e:
            print(f"Error calculating trial days: {e}")
            return self.license_data.get("max_trial_days", 7)
    
    def is_trial_expired(self):
        """Check if the trial period has expired"""
        return self.get_trial_days_left() <= 0
    
    def should_show_trial_message(self):
        """Check if we should show the trial expiration message"""
        return not self.is_license_active() and self.is_trial_expired()
    
    def get_license_status(self):
        """Get a dictionary with current license status"""
        days_left = self.get_trial_days_left()
        is_expired = self.is_trial_expired()
        
        if self.is_license_active():
            return {
                "active": True,
                "trial_days_left": days_left,
                "trial_expired": False,
                "message": "License activated"
            }
        elif is_expired:
            return {
                "active": False,
                "trial_days_left": 0,
                "trial_expired": True,
                "message": "Your trial has expired. Please purchase a license from whisperninja.app"
            }
        else:
            return {
                "active": False,
                "trial_days_left": days_left,
                "trial_expired": False,
                "message": f"Your trial expires in {days_left} day{'s' if days_left != 1 else ''}"
            }
    
    def validate_license_key(self, license_key):
        """
        Validate a license key via API call
        TODO: Implement actual API validation
        Returns: (is_valid: bool, message: str)
        """
        if not license_key or not license_key.strip():
            return False, "Please enter a license key"
        
        # API call to validate license key
        is_valid, message = validate_license_key(license_key)
        return is_valid, message
    
    def activate_license(self, license_key):
        """
        Activate a license key
        TODO: Implement actual API activation
        """
        # Validate the license key first
        is_valid, message = self.validate_license_key(license_key)
        
        if not is_valid:
            return False, message
        
        # API call to activate license
        is_activated, message = activate_license(license_key)
        if not is_activated:
            return False, message
        
        # Update license data
        self.license_data["is_license_activated"] = True
        self.license_data["license_key"] = license_key
        self._is_license_active = True  # Update cached value
        self.save_license()
        
        return True, "License activated successfully"
    
    def set_installation_timestamp(self, timestamp):
        """Set the installation timestamp to a specific value."""
        if isinstance(timestamp, datetime):
            formatted = timestamp.strftime("%Y-%m-%d %H:%M:%S")
        else:
            formatted = str(timestamp) if timestamp is not None else None
        self.license_data["installation_timestamp"] = formatted
        self.save_license()
    
    def get_license_key(self):
        """Get the stored license key"""
        return self.license_data.get("license_key", "")
