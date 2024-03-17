import os
import platform
import subprocess


def get_os():
    return platform.system()


def get_cpu_architecture():
    # e.g. x86_64, arm64
    return platform.machine()


def extract_app_version():
    result = subprocess.run(["youtube-bulk-upload", "--version"], capture_output=True, text=True)
    version = result.stdout.strip().split()[-1]
    return version


def write_to_github_env(vars_key_values_dict):
    github_env_filepath = os.getenv("GITHUB_ENV")
    print(f"Writing values to GITHUB_ENV file {github_env_filepath}:")

    with open(github_env_filepath, "a") as github_env_file:
        for key, value in vars_key_values_dict.items():
            github_env_file.write(f"{key}={value}\n")
            print(f" {key}={value}")


if __name__ == "__main__":
    vars = {
        "APPNAME": "YouTube Bulk Upload",
        "APPVERSION": extract_app_version(),
        "OPERATINGSYSTEM": get_os(),
        "ARCHITECTURE": get_cpu_architecture(),
    }

    vars["APPNAMEWITHDETAILS"] = f"{vars['APPNAME']} v{vars['APPVERSION']} ({vars['OPERATINGSYSTEM']} {vars['ARCHITECTURE']})"

    write_to_github_env(vars)
