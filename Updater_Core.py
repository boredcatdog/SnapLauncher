import tkinter as tk
from tkinter import ttk, messagebox
import os
import json
import hashlib
import urllib.request
import zipfile
import subprocess
import stat

# ===================== CONFIG =====================
BASE_PATH = "C:/Program Files/SnapLauncher"
INSTANCES_PATH = os.path.join(BASE_PATH, "instances")
ATLAUNCHER_JAR = os.path.join(BASE_PATH, "ATLauncher.jar")
MANIFEST_URL = "https://cdn.example.com/versions.json"  # replace with your CDN/Drive URL
TEMP_DOWNLOAD = os.path.join(BASE_PATH, "temp_download.zip")
OFFICIAL_PREFIX = "SnapClient"  # only enforce read-only on official packs
# ==================================================

class SnapUpdaterApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Snap Client Updater")
        self.geometry("400x150")
        self.resizable(False, False)

        # Dropdown
        self.label = tk.Label(self, text="Select Snap Pack version:")
        self.label.pack(pady=(20, 5))

        self.version_var = tk.StringVar()
        self.dropdown = ttk.Combobox(self, textvariable=self.version_var, state="readonly")
        self.dropdown.pack(pady=(0, 10))

        # Launch button
        self.launch_button = tk.Button(self, text="Download & Launch", command=self.download_and_launch)
        self.launch_button.pack(pady=(5, 10))

        # Status label
        self.status_label = tk.Label(self, text="", fg="green")
        self.status_label.pack()

        self.versions = []
        self.fetch_versions()

    # -------------------- FUNCTIONS --------------------
    def fetch_versions(self):
        try:
            with urllib.request.urlopen(MANIFEST_URL) as response:
                data = json.loads(response.read().decode())
                self.versions = data["versions"]
                self.dropdown["values"] = [v["name"] for v in self.versions]
                if self.versions:
                    self.version_var.set(self.versions[0]["name"])
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch versions: {e}")

    def download_and_launch(self):
        selected_name = self.version_var.get()
        if not selected_name:
            messagebox.showwarning("No Version", "Please select a version.")
            return

        # Find version info
        version_info = next((v for v in self.versions if v["name"] == selected_name), None)
        if not version_info:
            messagebox.showerror("Error", "Selected version not found.")
            return

        local_path = os.path.join(INSTANCES_PATH, selected_name)
        os.makedirs(local_path, exist_ok=True)

        # Remove read-only before updating if folder exists
        if os.listdir(local_path):
            self.remove_read_only(local_path)

        # Check if already downloaded
        if not os.listdir(local_path):
            self.status_label.config(text="Downloading...")
            self.update_idletasks()
            try:
                urllib.request.urlretrieve(version_info["url"], TEMP_DOWNLOAD)
            except Exception as e:
                messagebox.showerror("Download Error", str(e))
                return

            # Verify checksum
            if not self.verify_checksum(TEMP_DOWNLOAD, version_info["checksum"]):
                messagebox.showerror("Checksum Error", "Downloaded file is corrupted!")
                os.remove(TEMP_DOWNLOAD)
                return

            # Extract
            try:
                with zipfile.ZipFile(TEMP_DOWNLOAD, 'r') as zip_ref:
                    zip_ref.extractall(local_path)
                os.remove(TEMP_DOWNLOAD)
            except Exception as e:
                messagebox.showerror("Extraction Error", str(e))
                return

        # Set read-only if official Snap Client
        if selected_name.startswith(OFFICIAL_PREFIX):
            self.set_read_only(local_path)

        # Launch ATLauncher
        try:
            subprocess.Popen(["java", "-jar", ATLAUNCHER_JAR, f"--instance={local_path}"])
            self.status_label.config(text=f"Launched {selected_name}!")
        except Exception as e:
            messagebox.showerror("Launch Error", str(e))

    def verify_checksum(self, file_path, expected_hash):
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
        return sha256.hexdigest() == expected_hash

    def set_read_only(self, path):
        """Recursively set all files and folders to read-only."""
        for root, dirs, files in os.walk(path):
            for d in dirs:
                dir_path = os.path.join(root, d)
                os.chmod(dir_path, stat.S_IREAD | stat.S_IEXEC)
            for f in files:
                file_path = os.path.join(root, f)
                os.chmod(file_path, stat.S_IREAD)

    def remove_read_only(self, path):
        """Recursively remove read-only attribute for updates."""
        for root, dirs, files in os.walk(path):
            for d in dirs:
                dir_path = os.path.join(root, d)
                os.chmod(dir_path, stat.S_IWRITE | stat.S_IEXEC)
            for f in files:
                file_path = os.path.join(root, f)
                os.chmod(file_path, stat.S_IWRITE)

# -------------------- RUN --------------------
if __name__ == "__main__":
    os.makedirs(INSTANCES_PATH, exist_ok=True)
    app = SnapUpdaterApp()
    app.mainloop()
