import os
import subprocess

conf_dirpath = "/etc/wireguard"


def get_conf_path(iface_name: str):
    return os.path.join(conf_dirpath, f"{iface_name}.conf")


def generate_private():
    cmd = ["wg", "genkey"]
    process = subprocess.run(cmd, capture_output=True, text=True)
    if process.returncode == 0:
        return process.stdout.strip(), None

    return "", process.stderr


def generate_public(private):
    cmd = ["wg", "pubkey"]
    process = subprocess.run(cmd, input=private, capture_output=True, text=True)
    if process.returncode == 0:
        return process.stdout.strip(), None

    return "", process.stderr


def generate_keys():
    private, err = generate_private()
    public = None
    if err is None:
        public, err = generate_public(private)

    return private, public, err
