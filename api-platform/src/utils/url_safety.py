"""
出站 URL 安全校验（SSRF 防护）

背景：
    平台会根据仓库（Repository）配置的 `endpoint_url` 发起服务端出站请求
    （仓库转发、健康检查等）。若该地址可被任意填写，攻击者可将其指向
    内网服务或云厂商元数据地址，从而读取敏感信息（SSRF）。

防护策略：
    1. 仅允许 http / https 协议（阻断 file://、gopher://、dict:// 等协议探测）
    2. 一律阻断云厂商元数据地址（任何环境都不允许）
    3. 可选阻断私网 / 环回 / 链路本地 / 保留地址
       - 非生产环境默认允许（便于本地示例 API，如 http://localhost:8001）
       - 生产环境默认阻断（可通过 ALLOW_PRIVATE_REPO_ENDPOINTS 显式放行）
    4. 对域名做 DNS 解析后再校验解析结果，避免 127.0.0.1.nip.io、
       十进制 IP（如 2130706433）等绕过手法

使用方式：
    from src.utils.url_safety import ensure_outbound_url_allowed, OutboundURLBlocked

    try:
        ensure_outbound_url_allowed(url, allow_private=settings.private_repo_endpoints_allowed)
    except OutboundURLBlocked as exc:
        raise HTTPException(status_code=403, detail=str(exc))
"""

import ipaddress
import socket
from typing import List, Optional, Tuple
from urllib.parse import urlparse

from src.config.logging_config import get_logger

logger = get_logger("security")

# 允许的出站协议
ALLOWED_SCHEMES: Tuple[str, ...] = ("http", "https")

# 云厂商元数据地址：任何环境都必须阻断（一旦可访问即可窃取实例凭据）
METADATA_IPS = frozenset(
    {
        "169.254.169.254",  # AWS / Azure / GCP / 阿里云 通用元数据地址
        "169.254.170.2",    # AWS ECS 任务元数据
        "100.100.100.200",  # 阿里云元数据
        "fd00:ec2::254",    # AWS IPv6 元数据
    }
)

# 始终阻断的主机名（无论是否允许私网）
BLOCKED_HOSTNAMES = frozenset(
    {
        "metadata",
        "metadata.google.internal",
        "metadata.goog",
        "instance-data",
    }
)

# DNS 解析超时（秒）——避免校验阶段被慢 DNS 拖垮
DNS_TIMEOUT_SECONDS = 3.0


class OutboundURLBlocked(Exception):
    """出站地址被安全策略拒绝"""


def _parse_ip(value: str) -> Optional[ipaddress._BaseAddress]:
    """尝试把字符串解析为 IP 地址，失败返回 None"""
    try:
        return ipaddress.ip_address(value.strip())
    except ValueError:
        return None


def _is_always_blocked_ip(ip: ipaddress._BaseAddress) -> bool:
    """是否属于"任何环境都必须阻断"的地址（元数据）"""
    return str(ip) in METADATA_IPS


def _is_private_ip(ip: ipaddress._BaseAddress) -> bool:
    """
    是否属于私网 / 环回 / 链路本地 / 保留 / 组播 / 未指定地址。

    覆盖范围包含：
        - 环回   127.0.0.0/8、::1
        - 私网   10/8、172.16/12、192.168/16、fc00::/7
        - 链路本地 169.254/16、fe80::/10
        - 保留 / 未指定 / 组播
    """
    return any(
        (
            ip.is_private,
            ip.is_loopback,
            ip.is_link_local,
            ip.is_reserved,
            ip.is_multicast,
            ip.is_unspecified,
        )
    )


def _resolve_host(host: str, port: Optional[int]) -> List[ipaddress._BaseAddress]:
    """
    解析主机名为 IP 列表。

    Args:
        host: 主机名或 IP 字面量
        port: 端口（仅用于 getaddrinfo，可为 None）

    Returns:
        解析得到的 IP 列表；解析失败返回空列表
    """
    try:
        socket.setdefaulttimeout(DNS_TIMEOUT_SECONDS)
        infos = socket.getaddrinfo(host, port or 0, proto=socket.IPPROTO_TCP)
    except (socket.gaierror, socket.timeout, OSError) as exc:
        logger.warning("[URLSafety] DNS 解析失败: host=%s, err=%s", host, exc)
        return []
    finally:
        socket.setdefaulttimeout(None)

    ips: List[ipaddress._BaseAddress] = []
    for info in infos:
        addr = info[4][0]
        parsed = _parse_ip(addr)
        if parsed is not None and parsed not in ips:
            ips.append(parsed)
    return ips


def ensure_outbound_url_allowed(
    url: str,
    *,
    allow_private: bool = False,
    resolve_dns: bool = True,
) -> str:
    """
    校验出站 URL 是否允许访问，不允许则抛出 OutboundURLBlocked。

    Args:
        url: 待校验的完整 URL
        allow_private: 是否允许私网 / 环回地址
        resolve_dns: 是否对域名做 DNS 解析以校验解析结果（默认开启）

    Returns:
        原样返回 url（便于链式使用）

    Raises:
        OutboundURLBlocked: 地址不合法或被安全策略拒绝
    """
    if not url or not str(url).strip():
        raise OutboundURLBlocked("出站地址为空")

    raw = str(url).strip()

    try:
        parsed = urlparse(raw)
    except Exception as exc:  # pragma: no cover - urlparse 极少抛错
        raise OutboundURLBlocked(f"地址解析失败: {exc}")

    scheme = (parsed.scheme or "").lower()
    if scheme not in ALLOWED_SCHEMES:
        raise OutboundURLBlocked(
            f"不支持的协议 '{scheme or '(空)'}'，仅允许 http / https"
        )

    host = parsed.hostname
    if not host:
        raise OutboundURLBlocked("地址缺少主机名")

    host_norm = host.strip().strip("[]").lower()

    # 1) 显式阻断名单
    if host_norm in BLOCKED_HOSTNAMES or host_norm.endswith(".localhost"):
        raise OutboundURLBlocked(f"主机名被禁止访问: {host}")

    # 2) 主机名本身是 IP 字面量
    literal_ip = _parse_ip(host_norm)
    if literal_ip is not None:
        if _is_always_blocked_ip(literal_ip):
            raise OutboundURLBlocked(f"禁止访问云元数据地址: {host}")
        if _is_private_ip(literal_ip) and not allow_private:
            raise OutboundURLBlocked(f"禁止访问内网/环回地址: {host}")
        return raw

    # 3) 'localhost' 属于私网语义
    if host_norm == "localhost":
        if not allow_private:
            raise OutboundURLBlocked("禁止访问内网/环回地址: localhost")
        return raw

    # 4) 域名：解析后校验每一个结果，防止 DNS 指向内网
    if resolve_dns:
        ips = _resolve_host(host_norm, parsed.port)
        if not ips:
            # 无法解析：失败关闭（fail-closed），避免解析失败被绕过
            raise OutboundURLBlocked(f"域名无法解析，已拒绝访问: {host}")

        for ip in ips:
            if _is_always_blocked_ip(ip):
                raise OutboundURLBlocked(f"域名解析到云元数据地址，已拒绝: {host} -> {ip}")
            if _is_private_ip(ip) and not allow_private:
                raise OutboundURLBlocked(
                    f"域名解析到内网/环回地址，已拒绝: {host} -> {ip}"
                )

    return raw


def is_url_allowed(url: str, *, allow_private: bool = False) -> bool:
    """便捷判断（不抛异常），主要用于测试与日志"""
    try:
        ensure_outbound_url_allowed(url, allow_private=allow_private)
        return True
    except OutboundURLBlocked:
        return False
