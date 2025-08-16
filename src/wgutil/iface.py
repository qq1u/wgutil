import os
import ipaddress

from . import wg

iface_conf = """
[Interface]
Address = {ip}/32
ListenPort = {listen_port}
PrivateKey = {private_key}
PostUp = iptables -A FORWARD -i %i -j ACCEPT; iptables -t nat -I POSTROUTING -o {post_routing} -j MASQUERADE
PostUp = ip6tables -A FORWARD -i %i -j ACCEPT; ip6tables -t nat -I POSTROUTING -o {post_routing} -j MASQUERADE
PreDown = iptables -D FORWARD -i %i -j ACCEPT; iptables -t nat -D POSTROUTING -o {post_routing} -j MASQUERADE
PreDown = ip6tables -D FORWARD -i %i -j ACCEPT; ip6tables -t nat -D POSTROUTING -o {post_routing} -j MASQUERADE
"""  # noqa


def new_iface(
    iface_name: str,
    listen_port: int,
    post_routing: str,
    subnet: str,
    ip=None,
):
    conf_path = wg.get_conf_path(iface_name)
    if os.path.exists(conf_path):
        raise ValueError(f"wireguard interface conf exists: {conf_path!r}")

    network = ipaddress.IPv4Network(subnet, strict=False)
    if ip is None:
        ip = network.network_address + 1
    else:
        if ipaddress.IPv4Address(ip) not in network:
            raise ValueError(f"invalid ip: {ip!r}, network: {subnet!r}")

    private_key, err = wg.generate_private()
    if err is None:
        return iface_conf.format(
            ip=ip,
            listen_port=listen_port,
            private_key=private_key,
            post_routing=post_routing,
        )

    raise ValueError("wg generate private failed {}".format(err))
