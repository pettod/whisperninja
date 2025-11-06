import json
import os
from whisperninja.utils import resource_path
from datetime import datetime


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
        
        # Initialize installation timestamp if not set
        if not self.license_data.get("installation_timestamp"):
            self.set_installation_timestamp(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        LicenseManager._initialized = True
    
    def load_license(self):
        """Load license data from JSON file"""
        if os.path.exists(self.license_file):
            try:
                with open(self.license_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError) as e:
                print(f"Error loading license: {e}")
                return self._get_default_license_data()
        return self._get_default_license_data()
    
    def _get_default_license_data(self):
        """Get default license data structure"""
        return {
            "is_license_activated": False,
            "license_key": "",
            "max_trial_days": 7,
            "installation_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    
    def save_license(self):
        """Save license data to JSON file"""
        try:
            with open(self.license_file, 'w') as f:
                json.dump(self.license_data, f, indent=4)
            return True
        except Exception as e:
            print(f"Error saving license: {e}")
            return False
    
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
        
        # TODO: Make API call to validate license key
        # For now, stub implementation
        print(f"🔍 Validating license key: {license_key[:10]}...")
        
        # Stub: Return False for now
        return False, "License validation not yet implemented"
    
    def activate_license(self, license_key):
        """
        Activate a license key
        TODO: Implement actual API activation
        """
        # Validate the license key first
        is_valid, message = self.validate_license_key(license_key)
        
        if not is_valid:
            return False, message
        
        # TODO: Make API call to activate license
        # For now, stub implementation
        
        # Update license data
        self.license_data["is_license_activated"] = True
        self.license_data["license_key"] = license_key
        self._is_license_active = True  # Update cached value
        self.save_license()
        
        return True, "License activated successfully"
    
    def set_installation_timestamp(self, timestamp):
        """Set the installation timestamp"""
        self.license_data["installation_timestamp"] = timestamp
        self.save_license()
    
    def get_license_key(self):
        """Get the stored license key"""
        return self.license_data.get("license_key", "")
