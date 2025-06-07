"""
This code or file is part of 'BatteryPy' project
copyright (c) 2023-2025 , Aymen Brahim Djelloul, All rights reserved.
use of this source code is governed by MIT License that can be found on the project folder.

@author : Aymen Brahim Djelloul
version : 0.1
date : 06.04.2025
license : MIT License


"""

# IMPORTS
import os
import json
import threading
import webbrowser
import platform

import tkinter as tk
from pathlib import Path
from tkinter import ttk, messagebox, filedialog, PhotoImage, font
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from batterypy import BatteryPyException

try:
    import batterypy
    import requests
    miss_dependencies: bool = False

except ImportError:
    miss_dependencies: bool = True


class BatteryPyInterface:
    """
    This class contains the graphical user interface for the BatteryPy application.
    """

    def __init__(self, root) -> None:

        # Create root
        self.root = root

        # Set window title and size
        self.root.title(batterypy.caption)
        self.root.resizable(False, False)

        window_width: int = 420
        window_height: int = 550

        # Get screen dimensions
        screen_width: int = self.root.winfo_screenwidth()
        screen_height: int = self.root.winfo_screenheight()

        # Calculate center position
        x: int = (screen_width - window_width) // 2
        y: int = (screen_height - window_height) // 2

        # Set geometry
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")

        # Load icon (compact and safe)
        try:
            icon_path = os.path.join(os.path.dirname(__file__), "..", "images", "icon.png")
            icon = PhotoImage(file=icon_path)
            root.iconphoto(True, icon)

        except (tk.TclError, FileNotFoundError) as e:
            print(f"Warning: Could not load icon: {e}")

        # Configure enhanced font for messagebox
        default_font = font.nametofont("TkDefaultFont")

        default_font.configure(size=12, family="Segoe UI")

        caption_font = font.nametofont("TkCaptionFont")
        caption_font.configure(size=14, weight="bold", family="Segoe UI")

        if miss_dependencies:
            messagebox.showerror(
                "Missing Libraries",
                "One or more required components are missing.\n\n"
                "This application cannot start without the necessary libraries.\n"
                "Please ensure all dependencies are properly installed and try again."
            )

            self.root.destroy()  # close the app after showing the error
            return

        # Create an Updater object
        updater = Updater()

        if updater.is_update():
            # Get detailed update information
            update_info = updater.get_update_info()

            # Create a temporary root window to configure the default font
            temp_root = tk.Tk()
            temp_root.withdraw()  # Hide the window

            # Build the message with available information
            if update_info:
                new_version = update_info.get('version', 'Unknown')
                download_size = update_info.get('download_size_mb', 0)

                message: str = f" Update {new_version} ({download_size} MB) available. Install?"

                download_url: str = update_info.get('download_url', '')
            else:
                # Fallback message when update_info is unavailable
                message = (
                    " A new version of BatteryPy is available!\n\n"
                    "Would you like to download and install it?"
                )
                download_url = ''

            # Show update dialog with custom options
            response = messagebox.askyesnocancel(
                "⚡ BatteryPy Update Available",
                message,
                icon='question'
            )

            # Clean up temporary root
            temp_root.destroy()

            # Handle user response
            if response is True:  # Yes - Install
                target_url = download_url or f"{batterypy.website}#downloads"
                webbrowser.open_new(target_url)
            elif response is False:  # No - Remind later
                # Optional: Set reminder for later
                pass

        # Declare battery data
        self.battery_data: dict = {}

        try:
            # Create the Battery object
            self.battery: Optional = batterypy.Battery()

        except BatteryPyException:
            self.battery: None = None

        # Declare variables
        self.frame = None

        # Initialize the user interface
        self.create_ui()

    def create_ui(self) -> None:
        """Initial UI setup with a loading message. Data is populated later via threading."""

        # Check for battery presence
        if self.battery:

            # Start thread to load battery data
            threading.Thread(target=self._load_battery_data, daemon=True).start()

            # Declare the status label text
            status_text: str = "Please wait..."

            # Create title label
            self.title_label = ttk.Label(
                self.frame,
                text="BatteryPy - Check Your Battery",
                font=("Segoe UI", 12, "bold")
            )
            self.title_label.pack(pady=(0, 10))

        else:
            status_text: str = "BatteryPy is unable to detect battery on this device"

        # Create frame
        self.frame = ttk.Frame(self.root, padding=10)
        self.frame.pack(fill=tk.BOTH, expand=True)

        # Create info frame
        self.info_frame = ttk.LabelFrame(self.frame, text="Information", padding=15)
        self.info_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        # Create status label
        self.status_label = ttk.Label(
            self.info_frame,
            text=status_text,
            font=("Segoe UI", 11, "italic"),
            foreground="grey"
        )
        self.status_label.pack(pady=30)

        # Action buttons (disabled initially)
        self.button_frame = ttk.Frame(self.frame)
        self.button_frame.pack(pady=5)

        # Create a disabled save report button
        self.save_button = ttk.Button(
            self.button_frame, text="Save Report", command=self.save_report, state=tk.DISABLED
        )
        self.save_button.pack(side=tk.LEFT, padx=10)

        # Create about button
        self.about_button = ttk.Button(
            self.button_frame, text="About", command=self.show_about
        )
        self.about_button.pack(side=tk.LEFT, padx=10)

    def _load_battery_data(self) -> None:
        """Threaded method to get battery data and update UI on completion."""
        self.battery_data = self.battery.get_result()
        self.root.after(0, self._display_battery_info, self.battery_data)

    def _display_battery_info(self, data: Optional[dict]) -> None:
        """Update UI once battery data is available."""

        # Clear status message if exists
        if hasattr(self, "status_label"):
            self.status_label.destroy()

        if not data:
            ttk.Label(
                self.info_frame,
                text="BatteryPy Unable to retrieve data.",
                foreground="red",
                font=("Segoe UI", 12, "italic")

            ).pack(pady=30)
            return

        self.battery_data = data
        self.info_vars: dict[str, tk.StringVar] = {}
        self.info_labels: dict[str, ttk.Label] = {}  # Store labels for coloring

        for i, (key, value) in enumerate(data.items()):
            label_text = key.replace("_", " ").title()

            ttk.Label(self.info_frame, text=f"{label_text}  :", font=("Segoe UI", 10, "bold")).grid(
                row=i, column=0, sticky=tk.W, padx=(0, 10), pady=3
            )

            var = tk.StringVar(value=str(value))
            self.info_vars[key] = var

            value_label = ttk.Label(self.info_frame, textvariable=var, font=("Segoe UI", 11))
            value_label.grid(row=i, column=1, sticky=tk.W, pady=3)
            self.info_labels[key] = value_label  # Save label for updates

        # Enable buttons
        self.save_button.config(state=tk.NORMAL)

        # Start the periodic update loop with threading
        self._start_update_thread()

    def _start_update_thread(self):
        """Start a background thread to update battery data every 2 seconds."""

        def worker():
            """ This function is a worker to update battery info"""
            while True:
                updated_data: dict = {
                    "Power Status": "Plugged in" if self.battery.is_plugged() else "On Battery",
                    "Battery percentage": self.battery.battery_percent,
                    "Battery Voltage": self.battery.battery_voltage(),
                    "Battery Temperature": self.battery.battery_temperature()
                }

                print(updated_data)
                # Schedule GUI update in the main thread
                self.root.after(0, self._update, updated_data)
                threading.Event().wait(1)  # Sleep for 2 seconds

        threading.Thread(target=worker, daemon=True).start()

    def _update(self, updated_data: dict) -> None:
        """Update labels and color according to new values in the main thread."""

        for key, new_value in updated_data.items():
            if key in self.info_vars:
                old_value = self.info_vars[key].get()
                self.info_vars[key].set(str(new_value))

                label = self.info_labels.get(key)
                if label is not None:
                    try:
                        old_val_float = float(old_value)
                        new_val_float = float(new_value)
                    except Exception:
                        old_val_float = None
                        new_val_float = None

                    if old_val_float is not None and new_val_float is not None:
                        if new_val_float > old_val_float:
                            label.config(foreground="green")
                        elif new_val_float < old_val_float:
                            label.config(foreground="red")
                        else:
                            label.config(foreground="black")
                    else:
                        label.config(foreground="black")

    def save_report(self) -> None:
        """Save battery report with system info"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        default_name = f"battery_report_{platform.system().lower()}_{timestamp}"

        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("JSON files", "*.json")],
            initialfile=default_name,
            title="Save Battery Report"
        )

        if not file_path:
            return

        try:
            # Enhanced report data
            report_data: dict = {
                **self.battery_data,
                "system_info": {
                    "os": f"{platform.system()} {platform.release()}",
                    "machine": platform.machine(),
                    "app_version": getattr(self, 'app_version', batterypy.version),
                    "generated": datetime.now().strftime("%Y-%m-%d %H:%M")
                }
            }

            Path(file_path).parent.mkdir(parents=True, exist_ok=True)

            if file_path.lower().endswith('.json'):
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(report_data, f, indent=2)
            else:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write("BATTERY REPORT\n" + "=" * 50 + "\n\n")
                    for key, value in report_data.items():
                        if isinstance(value, dict):
                            f.write(f"{key.replace('_', ' ').title()}:\n")
                            for k, v in value.items():
                                f.write(f"  {k.replace('_', ' ').title()}: {v}\n")
                            f.write("\n")
                        else:
                            f.write(f"{key.replace('_', ' ').title()}: {value}\n")

            file_size = Path(file_path).stat().st_size / 1024
            messagebox.showinfo("Success",
                                f"Report saved successfully!\n"
                                f"Location: {Path(file_path).name}\n"
                                f"Size: {file_size:.1f} KB")

        except (PermissionError, OSError) as e:
            messagebox.showerror("Error", f"Failed to save report:\n{str(e)}")

        except Exception as e:
            messagebox.showerror("Error", f"Unexpected error:\n{str(e)}")

    def show_about(self) -> None:
        """Display an enhanced about dialog with professional styling"""

        # Create the about window
        about_window = tk.Toplevel(self.root)  # Assuming self.root is your main window
        about_window.title(f"About - {batterypy.caption}")
        about_window.geometry("400x350")
        about_window.resizable(False, False)
        about_window.transient(self.root)
        about_window.grab_set()

        # Center the window
        about_window.geometry("+%d+%d" % (
            self.root.winfo_rootx() + 50,
            self.root.winfo_rooty() + 50
        ))

        # Configure style
        style = ttk.Style()

        # Main frame with padding
        main_frame = ttk.Frame(about_window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # App icon/logo placeholder (you can replace with actual icon)
        icon_frame = ttk.Frame(main_frame)
        icon_frame.pack(pady=(0, 15))

        # App title
        title_label = ttk.Label(
            main_frame,
            text="BatteryPy",
            font=("Segoe UI", 16, "bold")
        )
        title_label.pack(pady=(0, 5))

        # Version
        version_label = ttk.Label(
            main_frame,
            text=f"Version {batterypy.version}",
            font=("Segoe UI", 10)
        )
        version_label.pack(pady=(0, 15))

        # Description
        desc_label = ttk.Label(
            main_frame,
            text="A comprehensive battery monitoring application\nbuilt with Python and Tkinter",
            font=("Segoe UI", 9),
            justify=tk.CENTER
        )
        desc_label.pack(pady=(0, 15))

        # Author info
        author_frame = ttk.Frame(main_frame)
        author_frame.pack(pady=(0, 15))

        ttk.Label(
            author_frame,
            text="Author:",
            font=("Segoe UI", 9, "bold")
        ).pack()

        ttk.Label(
            author_frame,
            text=batterypy.author,
            font=("Segoe UI", 9)
        ).pack()

        # Links frame
        links_frame = ttk.Frame(main_frame)
        links_frame.pack(pady=(0, 15))

        # Website button
        def open_website() -> None:
            """ This function will open the BatteryPy website"""
            webbrowser.open(batterypy.website)

        website_btn = ttk.Button(
            links_frame,
            text="🌐 Website",
            command=open_website,
            width=15
        )
        website_btn.pack(side=tk.LEFT, padx=(0, 10))

        # GitHub button
        def open_github() -> None:
            """ This function opens the GitHub url repository """
            webbrowser.open("https://github.com/aymenbrahimdjelloul/BatteryPy")

        github_btn = ttk.Button(
            links_frame,
            text="📁 GitHub",
            command=open_github,
            width=15
        )
        github_btn.pack(side=tk.LEFT)

        # Third-party libraries link
        def show_third_party() -> None:
            """ This function will show the third party software"""

            third_party_window = tk.Toplevel(about_window)
            third_party_window.title("Third-Party Libraries")
            third_party_window.geometry("450x380")
            third_party_window.resizable(False, False)
            third_party_window.transient(about_window)
            third_party_window.grab_set()

            # Center relative to about the window
            third_party_window.geometry("+%d+%d" % (
                about_window.winfo_rootx() + 25,
                about_window.winfo_rooty() + 25
            ))

            tp_frame = ttk.Frame(third_party_window, padding="20")
            tp_frame.pack(fill=tk.BOTH, expand=True)

            ttk.Label(
                tp_frame,
                text="Third-Party Libraries",
                font=("Segoe UI", 12, "bold")
            ).pack(pady=(0, 10))

            libraries_text: str = (
                "This application integrates the following open-source libraries:\n\n"
                "• BatteryPy – A utility library for accessing detailed battery status and power information.\n\n"
                "• tkinter – Python’s standard GUI toolkit, used to build the application's graphical user interface.\n\n"
                "We are deeply grateful to the developers and contributors of these libraries "
                "for their invaluable work in supporting the open-source ecosystem."
            )

            text_widget = tk.Text(tp_frame, wrap=tk.WORD, height=14, font=("Segoe UI", 11), relief="flat",
                                  bg=third_party_window.cget("bg"))
            text_widget.insert("1.0", libraries_text)
            text_widget.configure(state="disabled")
            text_widget.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

            ttk.Button(
                tp_frame,
                text="Close",
                command=third_party_window.destroy
            ).pack()

        third_party_link = ttk.Button(
            main_frame,
            text="View Third-Party Libraries",
            command=show_third_party,
            style="Link.TButton"
        )
        third_party_link.pack(pady=(0, 15))

        # Configure link button style
        style.configure("Link.TButton", foreground="blue")

        # Copyright
        copyright_label = ttk.Label(
            main_frame,
            text="© 2025 Aymen Brahim Djelloul. All rights reserved.",
            font=("Segoe UI", 10),
            foreground="gray"
        )
        copyright_label.pack(pady=(0, 5))

        # Focus and key bindings
        about_window.bind('<Escape>', lambda e: about_window.destroy())
        about_window.bind('<Return>', lambda e: about_window.destroy())


class Updater:
    """Updater class contains the logic to check for new updates from GitHub releases"""

    repo_owner: str = batterypy.author.replace(" ", "").lower()
    repo_name: str = "BatteryPy"

    # GitHub API URL for the latest release
    latest_release_url: str = f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases/latest"

    # Headers to avoid rate limiting and identify your app
    headers: dict[str, str] = {
        "User-Agent": f"{repo_name}-Updater/1.0",
        "Accept": "application/vnd.github.v3+json"
    }

    # Declare timeout
    timeout: int = 5

    # Cache settings
    cache_file: str = ".update_cache.json"
    cache_expiry_hours: int = 24

    def __init__(self) -> None:
        """
        Initialize the Updater

        Args:
            current_version: Current version of your application (e.g., "1.0.0")
            repo_owner: GitHub repository owner/organization name
            repo_name: GitHub repository name
        """

        self.r_session = requests.Session()
        self.r_session.headers.update(self.headers)

    def is_update(self) -> Optional[bool]:
        """
        Check if there's a new update available

        Returns:
            True if update available, False if current, None if error occurred
        """
        try:
            latest_info = self._get_latest_release_info()
            if not latest_info:
                return None

            latest_version = latest_info.get('version', '').lstrip('v')
            current_version = batterypy.version

            # Simple version comparison (you might want to use semantic versioning)
            return self._compare_versions(current_version, latest_version)

        except Exception as e:
            print(f"Error checking for updates: {e}")
            return None

    def get_update_info(self) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about the latest release

        Returns:
            Dictionary with the version, description, download_size_mb, download_url
        """
        try:
            return self._get_latest_release_info()
        except Exception as e:
            print(f"Error getting update info: {e}")
            return None

    def _get_latest_release_info(self) -> Optional[Dict[str, Any]]:
        """Get the latest release info with caching"""
        # Try to get from cache first
        cached_data = self._get_cached_data()
        if cached_data:
            return cached_data

        # Fetch fresh data
        response = self._request_latest_release()
        if not response:
            return None

        parsed_data = self._parse_latest_release(response)
        if parsed_data:
            self._save_to_cache(parsed_data)

        return parsed_data

    def _request_latest_release(self) -> Optional[requests.Response]:
        """Make HTTP request to GitHub API for the latest release"""
        try:
            response = self.r_session.get(
                self.latest_release_url,
                timeout=self.timeout
            )

            if response.status_code == 200:
                return response
            elif response.status_code == 404:
                print(f"Repository {self.repo_owner}/{self.repo_name} not found or no releases")
            elif response.status_code == 403:
                print("GitHub API rate limit exceeded")
            else:
                print(f"GitHub API returned status code: {response.status_code}")

            return None

        except requests.exceptions.Timeout:
            print("Request timed out")
            return None
        except requests.exceptions.ConnectionError:
            print("Connection error occurred")
            return None
        except Exception as e:
            print(f"Request error: {e}")
            return None

    def _parse_latest_release(self, response: requests.Response) -> Optional[Dict[str, Any]]:
        """Parse the GitHub latest release JSON response"""
        try:
            data = response.json()

            # Extract the main information
            version = data.get('tag_name', '')
            description = data.get('body', 'No description available')
            published_at = data.get('published_at', '')
            html_url = data.get('html_url', '')

            # Get download information from assets
            assets = data.get('assets', [])
            download_info = self._extract_download_info(assets)

            parsed_info = {
                'version': version,
                'description': description,
                'published_at': published_at,
                'html_url': html_url,
                'download_size_mb': download_info['size_mb'],
                'download_url': download_info['download_url'],
                'asset_name': download_info['asset_name'],
                'cached_at': datetime.now().isoformat()
            }

            return parsed_info

        except json.JSONDecodeError:
            print("Failed to parse JSON response")
            return None
        except Exception as e:
            print(f"Error parsing release data: {e}")
            return None

    @staticmethod
    def _extract_download_info(assets: list) -> Dict[str, Any]:
        """Extract download information from release assets"""

        if not assets:
            return {
                'size_mb': 0,
                'download_url': '',
                'asset_name': 'No assets available'
            }

        # Get the first asset (you might want to filter by platform/type)
        main_asset = assets[0]

        # Convert size from bytes to MB
        size_bytes = main_asset.get('size', 0)
        size_mb = round(size_bytes / (1024 * 1024), 2) if size_bytes > 0 else 0

        return {
            'size_mb': size_mb,
            'download_url': main_asset.get('browser_download_url', ''),
            'asset_name': main_asset.get('name', 'Unknown')
        }

    @staticmethod
    def _compare_versions(current: str, latest: str) -> bool:
        """
        Simple version comparison
        For production, consider using packaging.version for semantic versioning
        """
        try:
            # Remove 'v' prefix if present and split by dots
            current_parts = [int(x) for x in current.replace('v', '').split('.')]
            latest_parts = [int(x) for x in latest.replace('v', '').split('.')]

            # Pad shorter version with zeros
            max_len = max(len(current_parts), len(latest_parts))
            current_parts.extend([0] * (max_len - len(current_parts)))
            latest_parts.extend([0] * (max_len - len(latest_parts)))

            return latest_parts > current_parts

        except (ValueError, AttributeError):
            # Fallback to string comparison
            return latest > current

    def _get_cached_data(self) -> Optional[Dict[str, Any]]:
        """Get data from cache if it exists and hasn't expired"""
        try:
            with open(self.cache_file) as f:
                cached_data = json.load(f)

            cached_time = datetime.fromisoformat(cached_data.get('cached_at', ''))
            expiry_time = cached_time + timedelta(hours=self.cache_expiry_hours)

            if datetime.now() < expiry_time:
                return cached_data
            else:
                # Cache expired
                return None

        except (FileNotFoundError, json.JSONDecodeError, ValueError, KeyError):
            return None

    def _save_to_cache(self, data: Dict[str, Any]) -> None:
        """Save data to the cache file"""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Failed to save cache: {e}")

    def clear_cache(self) -> None:
        """Clear the cache file"""
        try:
            import os
            os.remove(self.cache_file)
            print("Cache cleared successfully")
        except FileNotFoundError:
            print("No cache file to clear")
        except Exception as e:
            print(f"Error clearing cache: {e}")


def main() -> None:
    """ This function will start the app"""

    root = tk.Tk()
    BatteryPyInterface(root)

    root.mainloop()


if __name__ == "__main__":
    main()
