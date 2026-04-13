from __future__ import annotations

import sys
import time
import shutil
import subprocess


def main() -> int:
    # Keep GUI in a separate file to avoid modifying wifi.py
    if sys.platform != "linux":
        print("The Palestinian Joker WiFi GUI works on Linux only.")
        return 1

    import tkinter as tk
    from tkinter import ttk, messagebox

    def run(cmd: list[str], timeout: float = 60.0) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )

    def have_nmcli() -> bool:
        return shutil.which("nmcli") is not None

    def wifi_ifaces_from_iw() -> list[str]:
        r = run(["iw", "dev"], timeout=10)
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

    def nmcli_ssids() -> list[str]:
        if not have_nmcli():
            return []
        run(["nmcli", "dev", "wifi", "rescan"], timeout=25)
        time.sleep(3)
        r = run(["nmcli", "-g", "SSID", "dev", "wifi"], timeout=90)
        if r.returncode != 0:
            return []
        ssids: list[str] = []
        for line in r.stdout.splitlines():
            s = line.strip()
            if s and s != "--" and s not in ssids:
                ssids.append(s)
        return ssids

    def try_connect_nmcli(ssid: str, password: str, iface: str) -> tuple[bool, str]:
        if not have_nmcli():
            return False, "nmcli is not available (NetworkManager)."
        if not ssid.strip():
            return False, "SSID is required."
        if not iface.strip():
            return False, "Wi‑Fi interface is required."

        run(["nmcli", "dev", "disconnect", iface], timeout=20)
        time.sleep(1)
        r = run(
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
        if r.returncode == 0:
            return True, f'Connected successfully to "{ssid}".'
        err = (r.stderr or r.stdout or "").strip()
        if err:
            return False, err
        return False, "Connection failed."

    root = tk.Tk()
    root.title("The Palestinian Joker WiFi")
    root.minsize(720, 480)

    mainf = ttk.Frame(root, padding=14)
    mainf.pack(fill="both", expand=True)

    ttk.Label(mainf, text="The Palestinian Joker WiFi", font=("Segoe UI", 18, "bold")).pack(anchor="w")
    ttk.Label(
        mainf,
        text="Connect to your own Wi‑Fi using the correct password (no wordlist).",
        foreground="#444",
    ).pack(anchor="w", pady=(0, 12))

    form = ttk.Frame(mainf)
    form.pack(fill="x")

    ttk.Label(form, text="Wi‑Fi Interface").grid(row=0, column=0, sticky="w", padx=(0, 10), pady=6)
    iface_var = tk.StringVar(value="")
    iface_combo = ttk.Combobox(form, textvariable=iface_var, values=[], state="readonly")
    iface_combo.grid(row=0, column=1, sticky="ew", pady=6)

    ttk.Label(form, text="SSID").grid(row=1, column=0, sticky="w", padx=(0, 10), pady=6)
    ssid_var = tk.StringVar(value="")
    ssid_combo = ttk.Combobox(form, textvariable=ssid_var, values=[])
    ssid_combo.grid(row=1, column=1, sticky="ew", pady=6)

    ttk.Label(form, text="Password").grid(row=2, column=0, sticky="w", padx=(0, 10), pady=6)
    pwd_var = tk.StringVar(value="")
    pwd_entry = ttk.Entry(form, textvariable=pwd_var, show="•")
    pwd_entry.grid(row=2, column=1, sticky="ew", pady=6)

    form.columnconfigure(1, weight=1)

    status_var = tk.StringVar(value="Ready.")
    ttk.Label(mainf, textvariable=status_var).pack(anchor="w", pady=(12, 8))

    log = tk.Text(mainf, height=10, wrap="word")
    log.pack(fill="both", expand=True)
    log.configure(state="disabled")

    def append(msg: str) -> None:
        log.configure(state="normal")
        log.insert("end", msg.rstrip() + "\n")
        log.see("end")
        log.configure(state="disabled")

    def refresh_ifaces() -> None:
        status_var.set("Detecting Wi‑Fi interfaces...")
        root.update_idletasks()
        ifaces = wifi_ifaces_from_iw()
        iface_combo["values"] = ifaces
        if ifaces and iface_var.get() not in ifaces:
            iface_var.set(ifaces[0])
        append("Interfaces: " + (", ".join(ifaces) if ifaces else "(none)"))
        status_var.set("Ready.")

    def scan_ssids() -> None:
        iface = iface_var.get().strip()
        if not iface:
            messagebox.showwarning("Missing interface", "Select a Wi‑Fi interface first.")
            return
        status_var.set("Scanning visible SSIDs...")
        root.update_idletasks()
        ssids = nmcli_ssids()
        ssid_combo["values"] = ssids
        if ssids and ssid_var.get() not in ssids:
            ssid_var.set(ssids[0])
        append(f"Scan results ({iface}): " + (", ".join(ssids) if ssids else "(none)"))
        status_var.set("Ready.")

    def connect() -> None:
        iface = iface_var.get().strip()
        ssid = ssid_var.get().strip()
        pwd = pwd_var.get()
        if not iface or not ssid:
            messagebox.showwarning("Missing info", "Select interface and SSID.")
            return
        status_var.set("Connecting...")
        root.update_idletasks()

        ok, msg = try_connect_nmcli(ssid, pwd, iface)

        append(("OK: " if ok else "ERR: ") + msg)
        status_var.set("Connected." if ok else "Ready.")
        if ok:
            messagebox.showinfo("Connected", msg)
        else:
            messagebox.showerror("Failed", msg)

    btns = ttk.Frame(mainf)
    btns.pack(fill="x", pady=(10, 0))
    ttk.Button(btns, text="Refresh Interfaces", command=refresh_ifaces).pack(side="left")
    ttk.Button(btns, text="Scan SSIDs", command=scan_ssids).pack(side="left", padx=8)
    ttk.Button(btns, text="Connect", command=connect).pack(side="right")

    refresh_ifaces()
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

