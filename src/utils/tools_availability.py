import subprocess
import shutil

def check_tool_availability():
    tools = ["dd", "find", "df", "du", "exiftool", "binwalk", "file", "ffmpeg", "sleuthkit", "disktype", "parted"]
    missing_tools = []

    for tool in tools:
        if shutil.which(tool) is None:
            missing_tools.append(tool)

    return missing_tools

def install_missing_tools(tools):
    results = []  # Store the results of each installation attempt

    for tool in tools:
        try:
            # Construct and run the installation command
            install_command = ["sudo", "apt", "install", tool, "-y"]
            subprocess.run(install_command, check=True)
            results.append(f"Successfully installed tool: {tool}")
        except subprocess.CalledProcessError:
            # Handle failed installations
            results.append(f"Failed to install tool: {tool}. Install it manually.")

    # Return the collected results as a single string
    return "\n".join(results)