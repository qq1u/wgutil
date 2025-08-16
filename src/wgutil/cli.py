import os
import sys
import json
import argparse
import ipaddress

import psutil

from .peer import new_peer


def get_default_post_routing():
    interfaces = psutil.net_if_addrs()
    for name in ["eth0", "enp3s0", "wlp2s0", "wlp3s0"]:
        if name in interfaces:
            return name
    return ""


def main():
    default_path = os.path.join(os.path.dirname(__file__), "default.json")
    default_json = {
        "iface_name": "wg0",
        "listen_port": 51820,
        "post_routing": get_default_post_routing(),
        "subnet": "10.0.0.0/24",
        "public_ip": "",
    }
    if os.path.exists(default_path):
        with open(default_path) as f:
            default_json = json.load(f)

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    default_parser = subparsers.add_parser("default", help="default values")
    default_parser.add_argument("--iface", required=False)
    default_parser.add_argument("--listen_port", required=False)
    default_parser.add_argument("--post_routing", required=False)
    default_parser.add_argument("--subnet", required=False)
    default_parser.add_argument("--public_ip", required=False)

    peer_parser = subparsers.add_parser("peer", help="add peer")
    peer_parser.add_argument("--ip", required=False)
    peer_parser.add_argument("--iface", required=False)
    peer_parser.add_argument("--endpoint", required=False)
    peer_parser.add_argument("--subnet", required=False)

    args = parser.parse_args()

    if args.command == "default":
        if args.iface:
            default_json["iface_name"] = args.iface

        if args.listen_port:
            if args.listen_port < 1024 or args.listen_port > 65535:
                print("invalid listen_port")
            else:
                default_json["listen_port"] = args.listen_port

        if args.post_routing and args.post_routing in psutil.net_if_addrs():
            default_json["post_routing"] = args.post_routing

        if args.subnet:
            try:
                ipaddress.IPv4Network(args.subnet, strict=False)
            except Exception:
                print("invalid subnet")
            else:
                default_json["subnet"] = args.subnet

        if args.endpoint:
            default_json["endpoint"] = args.endpoint

        with open(default_path, "w") as f:
            json.dump(default_json, f, indent=True)

        for key, value in default_json.items():
            print("{key!r}: {value!r}".format(key=key, value=value))

    elif args.command == "peer":
        iface = args.iface or default_json["iface_name"]

        endpoint = args.endpoint
        if not endpoint:
            public_ip = default_json["public_ip"]
            if not public_ip:
                print("required endpoint or public_ip")
                sys.exit(1)

            endpoint = "{public_ip}:{listen_port}".format(
                public_ip=public_ip, listen_port=default_json["listen_port"]
            )
        subnet = args.subnet or default_json["subnet"]
        new_peer(args.ip, iface, endpoint, subnet)

    else:
        parser.print_help()
