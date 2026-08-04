#!/usr/bin/env python3
"""
gpg_verify.py - XPM GPG 签名校验
用于校验 Release 文件和 .oil 包签名
"""

import subprocess
import os
import tempfile
import hashlib

class GPGError(Exception):
    pass

def verify_signature(data_path, sig_path, keyring=None):
    """
    验证 detached signature
    返回 (bool, message)
    """
    if not os.path.exists(data_path):
        return False, f"文件不存在: {data_path}"
    if not os.path.exists(sig_path):
        return False, f"签名文件不存在: {sig_path}"

    cmd = ["gpg", "--verify", sig_path, data_path]
    if keyring:
        cmd.extend(["--keyring", keyring])

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            return True, "签名验证通过"
        else:
            return False, result.stderr.strip() or result.stdout.strip()
    except FileNotFoundError:
        return False, "GPG 未安装"
    except subprocess.TimeoutExpired:
        return False, "GPG 验证超时"

def verify_release(Release_path, Release_gpg_path, trusted_keys=None):
    """
    验证 Release 文件的 GPG 签名
    Release_path: Packages.gz 对应的 Release 文件
    Release_gpg_path: Release.gpg 或 InRelease
    """
    return verify_signature(Release_path, Release_gpg_path, trusted_keys)

def import_key(key_url_or_path):
    """导入 GPG 公钥"""
    if key_url_or_path.startswith("http"):
        import urllib.request
        with urllib.request.urlopen(key_url_or_path, timeout=30) as resp:
            key_data = resp.read()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".gpg") as f:
            f.write(key_data)
            key_path = f.name
    else:
        key_path = key_url_or_path

    try:
        result = subprocess.run(
            ["gpg", "--import", key_path],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            return True, "密钥导入成功"
        return False, result.stderr.strip()
    finally:
        if key_url_or_path.startswith("http") and os.path.exists(key_path):
            os.unlink(key_path)

def sign_file(file_path, key_id, output_path=None):
    """用指定密钥签名文件"""
    cmd = ["gpg", "--detach-sign", "--armor", "--local-user", key_id]
    if output_path:
        cmd.extend(["--output", output_path])
    cmd.append(file_path)

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        raise GPGError(f"签名失败: {result.stderr.strip()}")
    return output_path or (file_path + ".asc")

def verify_package_integrity(oil_path, expected_sha256=None):
    """验证 .oil 包完整性"""
    h = hashlib.sha256()
    with open(oil_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    actual = h.hexdigest()

    if expected_sha256 and actual != expected_sha256:
        return False, f"SHA256 不匹配: 期望 {expected_sha256[:16]}..., 实际 {actual[:16]}..."
    return True, actual

def create_keyring(name="xpm-trusted"):
    """创建/初始化 XPM 专用 keyring"""
    keyring_dir = "/etc/xpm/trusted-keys"
    os.makedirs(keyring_dir, exist_ok=True)
    keyring_path = os.path.join(keyring_dir, f"{name}.gpg")

    # 初始化空 keyring
    subprocess.run(
        ["gpg", "--no-default-keyring", "--keyring", keyring_path, "--fingerprint"],
        capture_output=True, timeout=10
    )
    return keyring_path

if __name__ == "__main__":
    # 测试
    print("GPG 模块加载测试")
    print(f"GPG 可用: {os.system('which gpg > /dev/null 2>&1') == 0}")
