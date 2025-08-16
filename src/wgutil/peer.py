import os
import re
import ipaddress
import subprocess

import qrcode
from qrcode import constants as qrcode_constants

from . import wg

ADDRESS = "Address"
LISTEN_PORT = "ListenPort"
PRIVATE_KEY = "PrivateKey"
ALLOWED_IPS = "AllowedIPs"

persistent_keep_alive = "25"

peer_template = """
[Peer]
PublicKey = {public_key}
AllowedIPs = {allowed_ips}
PersistentKeepalive = {persistent_keep_alive}
""".lstrip()

peer_conf = """
[Interface]
PrivateKey = {private_key}
Address = {address}

[Peer]
PublicKey = {public_key}
AllowedIPs = {subnet}
Endpoint = {endpoint}
"""


def new_peer(ip, iface_name, endpoint, subnet):
    iface_conf_path = wg.get_conf_path(iface_name)
    if not os.path.exists(iface_conf_path):
        raise ValueError(f"invalid interface conf path: {iface_conf_path!r}")

    network = ipaddress.IPv4Network(subnet, strict=False)
    section = {}
    ips = []
    with open(iface_conf_path) as f:
        is_interface = False
        for line in f:
            if line.startswith("[Interface]"):
                is_interface = True
            elif line.startswith("[Peer]"):
                is_interface = False

            if is_interface:
                for key in [ADDRESS, LISTEN_PORT, PRIVATE_KEY]:
                    if line.startswith(key):
                        key, value, *_ = map(str.strip, line.split("=", 1))
                        section[key] = value
            else:
                if line.startswith(ALLOWED_IPS):
                    _, value, *_ = map(str.strip, line.split("=", 1))
                    for peer_ip in re.split(r",\s*", value):
                        if peer_ip.endswith("/32"):
                            peer_ip = peer_ip[:-3]

                        try:
                            peer_ip = ipaddress.IPv4Address(peer_ip)
                            if peer_ip in network:
                                ips.append(peer_ip)
                        except Exception:
                            pass

    if not ip:
        ips.append(network.network_address + 1)
        ips = sorted(ips)
        print("ips:", ips)
        ip = ips[-1] + 1
        print(ip)
    else:
        ip = ipaddress.IPv4Address(ip)
        if ip in ips:
            raise ValueError("ip exists")

    if ip not in network:
        raise ValueError("invalid ip")

    allowed_ip = f"{ip}/32"

    private, public, err = wg.generate_keys()
    if err is not None:
        raise ValueError("wg generate keys failed: {}".format(err))

    cmd = [
        "wg",
        "set",
        iface_name,
        "peer",
        public,
        "allowed-ips",
        allowed_ip,
        "persistent-keepalive",
        persistent_keep_alive,
    ]
    process = subprocess.run(cmd)
    if process.returncode != 0:
        raise Exception("exec cmd failed: {err}".format(err=process.stderr))

    append_peer = peer_template.format(
        public_key=public,
        allowed_ips=allowed_ip,
        persistent_keep_alive=persistent_keep_alive,
    )
    with open(iface_conf_path, "a") as f:
        f.write(append_peer)
        f.write("\n")

    client_public, err = wg.generate_public(section[PRIVATE_KEY])
    if err is not None:
        raise ValueError(
            "generate iface({iface}) public key failed: {err}".format(
                iface=iface_name, err=err
            )
        )

    client = peer_conf.format(
        private_key=private,
        address=allowed_ip,
        public_key=client_public,
        endpoint=endpoint,
        subnet=subnet,
    )
    print(client)
    print("-" * 66, "\n")

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode_constants.ERROR_CORRECT_M,
        box_size=8,
        border=2,
    )
    qr.add_data(client)
    qr.make(fit=True)
    qr.print_ascii(invert=True)
