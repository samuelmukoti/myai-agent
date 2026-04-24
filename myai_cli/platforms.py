"""
Shared platform registry for MyAIOne Agent.

Single source of truth for platform metadata consumed by both
skills_config (label display) and tools_config (default toolset
resolution).  Import ``PLATFORMS`` from here instead of maintaining
duplicate dicts in each module.
"""

from collections import OrderedDict
from typing import NamedTuple


class PlatformInfo(NamedTuple):
    """Metadata for a single platform entry."""
    label: str
    default_toolset: str


# Ordered so that TUI menus are deterministic.
PLATFORMS: OrderedDict[str, PlatformInfo] = OrderedDict([
    ("cli",            PlatformInfo(label="🖥️  CLI",            default_toolset="myai-cli")),
    ("telegram",       PlatformInfo(label="📱 Telegram",        default_toolset="myai-telegram")),
    ("discord",        PlatformInfo(label="💬 Discord",         default_toolset="myai-discord")),
    ("slack",          PlatformInfo(label="💼 Slack",           default_toolset="myai-slack")),
    ("whatsapp",       PlatformInfo(label="📱 WhatsApp",        default_toolset="myai-whatsapp")),
    ("signal",         PlatformInfo(label="📡 Signal",          default_toolset="myai-signal")),
    ("bluebubbles",    PlatformInfo(label="💙 BlueBubbles",     default_toolset="myai-bluebubbles")),
    ("email",          PlatformInfo(label="📧 Email",           default_toolset="myai-email")),
    ("homeassistant",  PlatformInfo(label="🏠 Home Assistant",  default_toolset="myai-homeassistant")),
    ("mattermost",     PlatformInfo(label="💬 Mattermost",      default_toolset="myai-mattermost")),
    ("matrix",         PlatformInfo(label="💬 Matrix",          default_toolset="myai-matrix")),
    ("dingtalk",       PlatformInfo(label="💬 DingTalk",        default_toolset="myai-dingtalk")),
    ("feishu",         PlatformInfo(label="🪽 Feishu",          default_toolset="myai-feishu")),
    ("wecom",          PlatformInfo(label="💬 WeCom",           default_toolset="myai-wecom")),
    ("wecom_callback", PlatformInfo(label="💬 WeCom Callback",  default_toolset="myai-wecom-callback")),
    ("weixin",         PlatformInfo(label="💬 Weixin",          default_toolset="myai-weixin")),
    ("qqbot",          PlatformInfo(label="💬 QQBot",           default_toolset="myai-qqbot")),
    ("webhook",        PlatformInfo(label="🔗 Webhook",         default_toolset="myai-webhook")),
    ("api_server",     PlatformInfo(label="🌐 API Server",      default_toolset="myai-api-server")),
])


def platform_label(key: str, default: str = "") -> str:
    """Return the display label for a platform key, or *default*."""
    info = PLATFORMS.get(key)
    return info.label if info is not None else default
