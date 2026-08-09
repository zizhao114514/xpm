"""
XPM Suite - 统一包管理器 + 应用商店
"Add Gui Store Edition"
"""

from .version import (
    VERSION_MAJOR, VERSION_MINOR, VERSION_PATCH, VERSION_SUFFIX,
    get_version_string, get_short_version, get_codename, get_full_name,
    get_version_tuple, parse_version, get_banner,
    get_cli_version_line, get_store_version_line, get_gui_title,
    COMPONENTS, get_component_version,
)
from .feature_flags import (
    check, require, list_features, disabled_features, FeatureError, FEATURES,
)

__version__ = get_version_string()
__codename__ = VERSION_SUFFIX
__fullname__ = "XPM Suite"

__all__ = [
    "VERSION_MAJOR", "VERSION_MINOR", "VERSION_PATCH", "VERSION_SUFFIX",
    "get_version_string", "get_short_version", "get_codename", "get_full_name",
    "get_version_tuple", "parse_version", "get_banner",
    "get_cli_version_line", "get_store_version_line", "get_gui_title",
    "COMPONENTS", "get_component_version",
    "check", "require", "list_features", "disabled_features", "FeatureError", "FEATURES",
]

# 初始化横幅（仅直接运行时打印）
if __name__ == "__main__":
    print(get_banner())
    print()
    list_features()
    print()
    disabled = disabled_features()
    if disabled:
        print(f"  ❌ 不可用功能({len(disabled)}): {', '.join(disabled)}")
    else:
        print("  ✅ 所有功能可用")
