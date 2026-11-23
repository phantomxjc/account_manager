# -*- coding: utf-8 -*-
"""网络探测模块：网址网络类型自动识别 + 网站连通性核实。

识别规则（按主人单位实际环境约定，由强到弱）：
1. 网址为 IP 且属于 10.x / 172.16-31.x   -> 政务外网（单位政务专线网段）
2. 网址为 IP 且属于 192.168.x            -> 家用网络（家庭路由器网段）
3. 域名以 .gov.cn 结尾或含 zwfw / 政务关键词 -> 政务外网
4. DNS 解析失败（仅内网 DNS 可解析的本机域名）-> 内网
5. 其余可达                              -> 互联网
"""
import ipaddress
import re
import socket
import time
import urllib.request
import urllib.error


def _extract_host(url):
    """从网址里取出主机名或 IP（去掉协议、端口、路径）。"""
    url = (url or "").strip()
    if not url:
        return ""
    url = re.sub(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", "", url)  # 去协议
    host = url.split("/")[0].split("?")[0]
    if "@" in host:            # 去掉 user@host 形式
        host = host.rsplit("@", 1)[-1]
    if ":" in host:            # 去端口（IPv6 方括号情况极少，忽略）
        host = host.split(":")[0]
    return host.strip()


def _parse_ip(host):
    """host 是合法 IP 则返回 ipaddress 对象，否则 None。"""
    try:
        return ipaddress.ip_address(host)
    except ValueError:
        return None


def _is_private_net(ip, networks):
    return any(ip in net for net in networks)


# 网段定义（IPv4）
NET_ZW = [ipaddress.ip_network(n) for n in
          ("10.0.0.0/8", "172.16.0.0/12")]          # 政务外网网段
NET_HOME = [ipaddress.ip_network("192.168.0.0/16")]  # 家用网络网段

# 政务关键词（域名）
GOV_KEYWORDS = ("zwfw", "zw", "政务", "gov.cn")


def detect_network_type(url):
    """识别网址所属网络类型，返回 (类型, 依据说明)。"""
    host = _extract_host(url)
    if not host:
        return "", "网址为空"

    ip = _parse_ip(host)
    if ip is not None:
        if _is_private_net(ip, NET_ZW):
            return "政务外网", f"{host} 属政务专线网段(10.x/172.16-31.x)"
        if _is_private_net(ip, NET_HOME):
            return "家用网络", f"{host} 属 192.168.x 家用网段"
        return "互联网", f"{host} 为公网 IP"

    low = host.lower()
    if low.endswith(".gov.cn") or any(k in low for k in GOV_KEYWORDS[:3]) \
            or "gov.cn" in low or "政务" in host:
        return "政务外网", f"{host} 为政务域名(.gov.cn/zwfw)"

    # DNS 解析探测：解析失败通常意味着只有内网 DNS 才能解析 -> 内网
    try:
        socket.setdefaulttimeout(3)
        socket.getaddrinfo(host, None)
        return "互联网", f"{host} 公网 DNS 可解析"
    except OSError:
        return "内网", f"{host} 无法公网解析（仅内网 DNS 可达）"


def verify_website(url, timeout=5):
    """核实网站连通性。

    返回 (ok: bool, detail: str, cost_ms: int)
    detail 形如 "HTTP 200"、"HTTP 403"、"超时"、"无法解析"、"连接被拒绝"。
    """
    url = (url or "").strip()
    if not url:
        return False, "网址为空", 0
    if "://" not in url:
        url = "http://" + url

    start = time.time()
    try:
        req = urllib.request.Request(url, method="HEAD",
                                     headers={"User-Agent": "Mozilla/5.0 (MoxiangVerify)"})
        resp = urllib.request.urlopen(req, timeout=timeout)
        cost = int((time.time() - start) * 1000)
        return True, f"HTTP {resp.status}", cost
    except urllib.error.HTTPError as e:
        cost = int((time.time() - start) * 1000)
        # 有 HTTP 响应即视为"可访问"（403/404 也说明站点活着）
        return True, f"HTTP {e.code}", cost
    except urllib.error.URLError as e:
        cost = int((time.time() - start) * 1000)
        reason = getattr(e, "reason", e)
        text = str(reason)
        if "timed out" in text or "timeout" in text.lower():
            return False, "超时", cost
        if "getaddrinfo" in text or "Name or service" in text or "nodename" in text.lower():
            return False, "无法解析", cost
        if "refused" in text.lower():
            return False, "连接被拒绝", cost
        return False, text or "无法连接", cost
    except socket.timeout:
        return False, "超时", int((time.time() - start) * 1000)
    except Exception as e:  # 兜底
        return False, str(e)[:40] or "无法连接", int((time.time() - start) * 1000)
