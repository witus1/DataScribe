import os
import json

# Define the relative path for the configuration file
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../config.json")

def load_config():
    """
    Load the configuration from the project-relative config file.
    Handle cases where the file is missing, empty, or invalid.
    """
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            # Log the issue and recreate a valid default config
            return recreate_default_config()
    return recreate_default_config()

def recreate_default_config():
    """
    Recreate a valid default configuration file.
    """
    default_config = {"workdir": os.getcwd()}
    save_config(default_config)
    return default_config

def save_config(config):
    """
    Save the configuration to the project-relative config file.
    """
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

def set_working_directory(path):
    """
    Set the global working directory and persist it in the config file.
    """
    if os.path.exists(path) and os.path.isdir(path):
        config = load_config()
        config["workdir"] = os.path.abspath(path)
        save_config(config)
    else:
        raise ValueError(f"Invalid directory: {path}")

def get_working_directory():
    """
    Get the global working directory from the config file.
    """
    config = load_config()
    return config.get("workdir", os.getcwd())
