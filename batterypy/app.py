#!/usr/bin/env python3

"""
This code or file is part of 'BatteryPy' project
copyright (c) 2023-2025 , Aymen Brahim Djelloul, All rights reserved.
use of this source code is governed by MIT License that can be found on the project folder.

@_AUTHOR : Aymen Brahim Djelloul
VERSION : 0.2
date : 06.04.2025
license : MIT License


"""

# IMPORTS
import os
import json
import sys
import threading
import webbrowser
import platform
import ctypes
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


def _run_as_admin() -> Optional[Any]:
    """
    Relaunch the script with admin privileges if not already running as admin.
    Returns True if already admin or successfully relaunched, False otherwise.
    """
    try:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin()

    except Exception:
        is_admin = False

    if is_admin:
        return True  # Already running as admin
    else:
        # Relaunch with admin privileges
        try:
            script = os.path.abspath(sys.argv[0])
            params = " ".join([f'"{arg}"' for arg in sys.argv[1:]])
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, f'"{script}" {params}', None, 1)
            sys.exit(0)
        except Exception as e:
            print(f"Failed to relaunch as admin: {e}")
            return False


class BatteryPyInterface:
    """
    This class contains the graphical user interface for the BatteryPy application.
    Optimized for fast, reliable 2-second battery updates.
    """

    def __init__(self, root) -> None:
        # Create root
        self.root = root

        # Set window title and size
        self.root.title(getattr(batterypy, '_CAPTION', 'BatteryPy'))
        self.root.resizable(False, False)

        window_width: int = 430
        window_height: int = 570

        # Get screen dimensions
        screen_width: int = self.root.winfo_screenwidth()
        screen_height: int = self.root.winfo_screenheight()

        # Calculate center position
        x: int = (screen_width - window_width) // 2
        y: int = (screen_height - window_height) // 2

        # Set geometry
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")

        # Set window icon
        self._set_icon(self.root)

        # Check for missing dependencies
        if miss_dependencies:

            messagebox.showerror(
                "Missing Libraries",
                "One or more required components are missing.\n\n"
                "This application cannot start without the necessary libraries.\n"
                "Please ensure all dependencies are properly installed and try again."
            )
            self.root.destroy()
            return

        # Configure enhanced font for messagebox
        try:
            default_font = font.nametofont("TkDefaultFont")
            default_font.configure(size=12, family="Segoe UI")

            caption_font = font.nametofont("TkCaptionFont")
            caption_font.configure(size=14, weight="bold", family="Segoe UI")

        except Exception as e:
            print(f"Font configuration warning: {e}")

        # Check for updates
        # Create Updater object
        updater = Updater()

        if updater.is_update():
            update_data = updater.get_update_info()

            version: str = update_data.get("VERSION", "N/A")
            size: str = update_data.get("download_size_mb", "Unknown")
            description: str = update_data.get("description", "No description provided.")
            download_url: str = update_data.get("download_url")

            # Show message box
            root = tk.Tk()
            root.withdraw()  # Hide the root window

            message: tuple[str] = (
                f"A new VERSION of BatteryPy is available!\n\n"
                f"Version: {version}\n"
                f"Size: {size}\n\n"
                f"Description:\n{description}\n\n"
                f"Would you like to open the update page?"
            )

            if messagebox.askyesno("Update Available", message):
                webbrowser.open(download_url)

            root.destroy()

        # Initialize battery and UI components
        self._initialize_battery()
        self._initialize_variables()

        # Set up cleanup on window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

        # Initialize the user interface
        self.create_ui()

    def _initialize_battery(self) -> None:
        """Initialize battery object safely."""
        try:
            self.battery = batterypy.Battery()
        except BatteryPyException:
            self.battery = None

    def _initialize_variables(self) -> None:
        """Initialize instance variables."""
        self.battery_data: Dict[str, Any] = {}
        self.info_vars: Dict[str, tk.StringVar] = {}
        self.info_labels: Dict[str, ttk.Label] = {}

        # UI components
        self.frame = None
        self.info_frame = None
        self.status_label = None
        self.title_label = None
        self.save_button = None
        self.about_button = None
        self.button_frame = None

        # Update thread control
        self.update_running = False
        self.update_thread = None

    @staticmethod
    def _set_icon(parent: tk.Tk) -> None:
        """Set window icon on Windows with fallback to generic Windows-style icon."""

        try:
            icon_png = "icon.png"
            if os.path.exists(icon_png):
                icon = PhotoImage(file=icon_png)
                parent.iconphoto(True, icon)
                return
            else:
                print(f"Warning: Icon file not found at {icon_png}")
        except Exception as e:
            print(f"Warning: Could not load PNG icon: {e}")

        # Fallback: Use bundled Windows-style .ico
        try:
            fallback_ico = "fallback.ico"  # Must be present in your project
            if os.path.exists(fallback_ico):
                parent.iconbitmap(fallback_ico)
            else:
                print(f"Warning: fallback.ico not found.")
        except Exception as e:
            print(f"Warning: Could not set fallback icon: {e}")

    def create_ui(self) -> None:
        """Initial UI setup with optimized layout."""

        # Create main frame
        self.frame = ttk.Frame(self.root, padding=10)
        self.frame.pack(fill=tk.BOTH, expand=True)

        # Create info frame
        self.info_frame = ttk.LabelFrame(self.frame, text="Information", padding=15)
        self.info_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        if self.battery:
            # Start loading battery data
            self._load_initial_data()
        else:
            # Show no battery message
            self.status_label = ttk.Label(
                self.info_frame,
                text="No battery detected !",
                font=("Segoe UI", 11, "italic"),
                foreground="red"
            )
            self.status_label.pack(pady=30)

        # Create action buttons
        self._create_buttons()

    def _create_buttons(self) -> None:
        """Create action buttons."""
        self.button_frame = ttk.Frame(self.frame)
        self.button_frame.pack(pady=0)

        # Save report button
        self.save_button = ttk.Button(
            self.button_frame,
            text="Save",
            command=self.save_report,
            state=tk.DISABLED
        )
        self.save_button.pack(side=tk.LEFT, padx=10)

        # About button
        self.about_button = ttk.Button(
            self.button_frame,
            text="About",
            command=self.show_about
        )
        self.about_button.pack(side=tk.LEFT, padx=10)

    def _load_initial_data(self) -> None:
        """Load initial battery data."""
        # Show loading message
        self.status_label = ttk.Label(
            self.info_frame,
            text="Loading battery information...",
            font=("Segoe UI", 11, "italic"),
            foreground="grey"
        )
        self.status_label.pack(pady=30)

        # Start thread to load data
        threading.Thread(target=self._load_battery_data, daemon=True).start()

    def _load_battery_data(self) -> None:
        """Threaded method to get initial battery data."""
        try:
            if self.battery:
                self.battery_data = self.battery.get_result()
                self.root.after(0, self._display_battery_info, self.battery_data)
            else:
                self.root.after(0, self._display_battery_info, None)
        except Exception as e:
            print(f"Error loading battery data: {e}")
            self.root.after(0, self._display_battery_info, None)

    def _display_battery_info(self, data: Optional[Dict[str, Any]]) -> None:
        """Display battery information in the UI."""

        # Clear loading message
        if self.status_label:
            self.status_label.destroy()
            self.status_label = None

        if not data:
            error_label = ttk.Label(
                self.info_frame,
                text="Unable to retrieve battery data",
                foreground="red",
                font=("Segoe UI", 12, "italic")
            )
            error_label.pack(pady=30)
            return

        # Store data and create display
        self.battery_data: dict = data
        self.info_vars: dict = {}
        self.info_labels: dict = {}

        # Configure grid
        self.info_frame.columnconfigure(1, weight=1)

        # Create labels for each data item
        for i, (key, value) in enumerate(data.items()):
            self._create_info_row(i, key, value)

        # Enable save button
        self.save_button.config(state=tk.NORMAL)

        # Start updates
        self._start_updates()

    def _create_info_row(self, row: int, key: str, value: Any) -> None:
        """Create a row of information display."""
        label_text = key.replace("_", " ").title()

        # Key label
        key_label = ttk.Label(
            self.info_frame,
            text=f"{label_text}:",
            font=("Segoe UI", 10, "bold")
        )
        key_label.grid(row=row, column=0, sticky=tk.W, padx=(0, 15), pady=5)

        # Value variable and label
        var = tk.StringVar(value=str(value))
        self.info_vars[key] = var

        value_label = ttk.Label(
            self.info_frame,
            textvariable=var,
            font=("Segoe UI", 11)
        )
        value_label.grid(row=row, column=1, sticky=tk.W, pady=5)
        self.info_labels[key] = value_label

    def _start_updates(self) -> None:
        """Start battery monitoring updates every 1 second."""
        if not self.battery:
            return

        # Stop any existing updates first
        self.update_running = False

        # Give time for existing thread to stop
        self.root.after(100, self._start_update_loop)

    def _start_update_loop(self) -> None:
        """Initialize the update loop."""
        self.update_running = True
        self._schedule_next_update()

    def _schedule_next_update(self) -> None:
        """Schedule the next update using tkinter after method (thread-safe)."""

        if not self.update_running:
            return

        try:
            # Get battery data
            current_data: dict[str, str] = {
                "power_status": "Plugged in" if self.battery.is_plugged() else "On Battery",
                "charge_rate": f"{self.battery.charge_rate() / 1000:.0f} Watts",
                "fast_charge": "Yes" if self.battery.is_fast_charge() else "No",
                "battery_percent": f"{self.battery.battery_percent()}%",
                "battery_voltage": f"{self.battery.battery_voltage()} V",
            }

            # Update display immediately
            self._update_display(current_data)

        except Exception as e:
            print(f"Update error: {e}")

        # Schedule next update in 1000ms (1 second)
        if self.update_running:
            self.root.after(1000, self._schedule_next_update)

    def _update_display(self, new_data: Dict[str, str]) -> None:
        """Update display labels with new data and apply visual feedback."""
        if not hasattr(self, 'info_vars') or not self.info_vars:
            return

        for key, new_value in new_data.items():
            if key not in self.info_vars:
                continue

            try:
                # Get old value before updating
                old_value: str = self.info_vars[key].get()

                # Update the tkinter StringVar
                self.info_vars[key].set(new_value)

                # Apply color feedback if labels exist
                if hasattr(self, 'info_labels') and key in self.info_labels:
                    self._apply_color_feedback(key, old_value, new_value)

            except Exception as e:
                print(f"Display update error for {key}: {e}")

    def _apply_color_feedback(self, key: str, old_value: str, new_value: str) -> None:
        """Apply color feedback for value changes with improved logic."""
        if key not in self.info_labels:
            return

        try:
            label = self.info_labels[key]
            color = "black"  # Default color

            # Handle power status changes
            if key == "power_status":
                if "Plugged" in new_value and "Battery" in old_value:
                    color = "green"  # Plugged in = good
                elif "Battery" in new_value and "Plugged" in old_value:
                    color = "orange"  # On battery = warning

            # Handle numeric value changes
            elif old_value != new_value:  # Only process if values actually changed
                old_num = self._extract_number(old_value)
                new_num = self._extract_number(new_value)

                if old_num is not None and new_num is not None:
                    if key == "battery_percent":
                        # Battery percentage: green for increase, red for decrease
                        if new_num > old_num:
                            color = "green"
                        elif new_num < old_num:
                            color = "red"
                    elif key == "battery_voltage":
                        # Voltage: more subtle feedback
                        voltage_diff = abs(new_num - old_num)
                        if voltage_diff > 0.1:  # Significant voltage change
                            color = "blue" if new_num > old_num else "purple"

            # Apply color with fade-back effect
            if color != "black":
                label.config(foreground=color)
                # Reset color after 1.2 seconds (shorter than update interval)
                self.root.after(1200, lambda lbl=label: lbl.config(foreground="black"))

        except Exception as e:
            print(f"Color feedback error for {key}: {e}")

    @staticmethod
    def _extract_number(value: str) -> float | None:
        """Extract numeric value from string, return None if not found."""
        try:
            # Remove common units and extract number
            cleaned = ''.join(c for c in value if c.isdigit() or c in '.,-')
            cleaned = cleaned.replace(',', '.')  # Handle different decimal separators
            return float(cleaned) if cleaned else None

        except (ValueError, TypeError):
            return None

    def stop_updates(self) -> None:
        """ This method will stop updates"""

        # Wait for thread to finish
        if hasattr(self, 'update_thread') and self.update_thread:
            try:
                self.update_thread.join(timeout=2.0)
            except Exception as e:
                print(f"Thread cleanup error: {e}")

    def save_report(self) -> None:
        """Save battery report with system info."""
        if not self.battery_data:
            messagebox.showwarning("Warning", "No battery data available to save.")
            return

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
            # Create enhanced report data
            report_data = {
                **self.battery_data,
                "system_info": {
                    "os": f"{platform.system()} {platform.release()}",
                    "machine": platform.machine(),
                    "app_version": getattr(batterypy, 'VERSION', '1.0.0'),
                    "generated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
            }

            # Ensure directory exists
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)

            # Save file
            if file_path.lower().endswith('.json'):
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(report_data, f, indent=2, ensure_ascii=False)
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

            # Show success message
            file_size = Path(file_path).stat().st_size / 1024
            messagebox.showinfo(
                "Success",
                f"Report saved successfully!\n"
                f"Location: {Path(file_path).name}\n"
                f"Size: {file_size:.1f} KB"
            )

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save report:\n{str(e)}")

    def show_about(self) -> None:
        """Display about dialog with improved error handling and structure."""
        try:
            # Create about window
            about_window = tk.Toplevel(self.root)
            about_window.title("About - BatteryPy")
            about_window.geometry("420x350")
            about_window.resizable(False, False)
            # about_window.transient(self.root)
            # about_window.grab_set()

            # Center the window relative to parent
            self._center_window(about_window, self.root, 10, 10)

            # Configure window icon if available
            if hasattr(self, 'icon_path'):
                try:
                    about_window.iconbitmap(self.icon_path)
                except tk.TclError:
                    pass  # Icon not found, continue without it

            # Main frame with better padding
            main_frame = ttk.Frame(about_window, padding="25")
            main_frame.pack(fill=tk.BOTH, expand=True)

            # App info section
            self._create_app_info_section(main_frame)

            # Separator
            ttk.Separator(main_frame, orient='horizontal').pack(fill=tk.X, pady=(15, 20))

            # Author section
            self._create_author_section(main_frame)

            # Links section
            self._create_links_section(main_frame, about_window)

            # Third-party libraries link
            self._create_third_party_link(main_frame, about_window)

            # Copyright section
            self._create_copyright_section(main_frame)

            # Key bindings
            about_window.bind('<Escape>', lambda e: about_window.destroy())
            about_window.bind('<Return>', lambda e: about_window.destroy())

            # Focus on window
            about_window.focus_set()

        except Exception as e:
            # Fallback error handling
            print(f"Error creating about dialog: {e}")
            if 'about_window' in locals():
                about_window.destroy()

    @staticmethod
    def _center_window(window, parent, offset_x=0, offset_y=0) -> None:
        """Center a window relative to its parent with optional offset."""

        # window.update_idletasks()  # Ensure geometry is up-to-date

        # Get parent geometry
        px, py = parent.winfo_rootx(), parent.winfo_rooty()
        pw, ph = parent.winfo_width(), parent.winfo_height()

        # Get window requested size
        ww, wh = window.winfo_reqwidth(), window.winfo_reqheight()

        # Calculate centered position with offsets
        x = px + (pw - ww) // 2 + offset_x
        y = py + (ph - wh) // 2 + offset_y

        # Clamp coordinates to screen bounds
        screen_w, screen_h = window.winfo_screenwidth(), window.winfo_screenheight()
        x = max(0, min(x, screen_w - ww))
        y = max(0, min(y, screen_h - wh))

        window.geometry(f"+{x}+{y}")

    @staticmethod
    def _create_app_info_section(parent) -> None:
        """Create the application information section."""
        # App title with better styling
        title_label = ttk.Label(
            parent,
            text="BatteryPy",
            font=("Segoe UI", 14, "bold")
        )
        title_label.pack(pady=(0, 8))

        # Version with fallback
        version = getattr(batterypy, 'VERSION', '1.0.0')
        version_label = ttk.Label(
            parent,
            text=f"Version {version}",
            font=("Segoe UI", 10),
            foreground="gray"
        )
        version_label.pack(pady=(0, 5))

        # Description with better formatting
        description = (
            "A comprehensive battery monitoring application\n"
            "Monitor your system's power status, battery health,\n"
            "and charging information in real-time."
        )

        desc_label = ttk.Label(
            parent,
            text=description,
            font=("Segoe UI", 9),
            justify=tk.CENTER,
            foreground="gray"
        )
        desc_label.pack(pady=(0, 5))

    @staticmethod
    def _create_author_section(parent) -> None:
        """Create the _AUTHOR information section."""
        author_frame = ttk.Frame(parent)
        author_frame.pack(pady=(0, 5))

        # Author label
        ttk.Label(
            author_frame,
            text="Author:",
            font=("Segoe UI", 9, "bold")
        ).pack()

        # Author name with fallback
        author_name = getattr(batterypy, '_AUTHOR', 'Aymen Brahim Djelloul')
        ttk.Label(
            author_frame,
            text=author_name,
            font=("Segoe UI", 9)
        ).pack(pady=(2, 0))

    @staticmethod
    def _create_links_section(parent, about_window) -> None:
        """Create the links section with _WEBSITE and GitHub buttons."""
        links_frame = ttk.Frame(parent)
        links_frame.pack(pady=(0, 15))

        # Website button
        def open_website():
            try:
                url = getattr(batterypy, '_WEBSITE', 'https://github.com/aymenbrahimdjelloul/BatteryPy')
                webbrowser.open(url)
            except Exception as e:
                print(f"Error opening _WEBSITE: {e}")

        website_btn = ttk.Button(
            links_frame,
            text="🌐 Website",
            command=open_website,
            width=15
        )
        website_btn.pack(side=tk.LEFT, padx=(0, 10))

        # GitHub button
        def open_github():
            try:
                webbrowser.open("https://github.com/aymenbrahimdjelloul/BatteryPy")
            except Exception as e:
                print(f"Error opening GitHub: {e}")

        github_btn = ttk.Button(
            links_frame,
            text="📁 GitHub",
            command=open_github,
            width=15
        )
        github_btn.pack(side=tk.LEFT)

    def _create_third_party_link(self, parent, about_window) -> None:
        """Create the third-party libraries link."""

        def show_third_party():
            try:
                self._show_third_party_dialog(about_window)
            except Exception as e:
                print(f"Error showing third-party dialog: {e}")

        # Configure link button style if not already done
        style = ttk.Style()
        style.configure("Link.TButton", foreground="blue", relief="flat")
        style.map("Link.TButton",
                  foreground=[('active', 'darkblue')])

        third_party_link = ttk.Button(
            parent,
            text="📚 View Third-Party Libraries",
            command=show_third_party,
            style="Link.TButton"
        )
        third_party_link.pack(pady=(0, 10))

    def _show_third_party_dialog(self, parent_window) -> None:
        """Show the third-party libraries dialog."""
        # Create third-party window
        tp_window = tk.Toplevel(parent_window)
        tp_window.title("Third-Party Libraries")
        tp_window.geometry("480x400")
        tp_window.resizable(False, False)
        # tp_window.transient(parent_window)
        # tp_window.grab_set()

        # Center relative to parent
        self._center_window(tp_window, parent_window, 25, 25)

        # Main frame
        tp_frame = ttk.Frame(tp_window, padding="20")
        tp_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        ttk.Label(
            tp_frame,
            text="Third-Party Libraries",
            font=("Segoe UI", 12, "bold")
        ).pack(pady=(0, 10))

        # Libraries information
        libraries_text: str = (
            "This application integrates the following open-source libraries:\n\n"
            "• BatteryPy – Cross-platform library for monitoring, "
            "providing detailed battery and power information.\n\n"
            "• tkinter – Python's standard GUI toolkit, used to build the "
            "application's graphical user interface.\n\n"
            "We are deeply grateful to the developers and contributors of these "
            "libraries for their invaluable work in supporting the open-source ecosystem.\n\n"
            "For more information about these libraries, please visit their respective "
            "project pages and documentation."
        )

        # Create scrollable text widget
        text_frame = ttk.Frame(tp_frame)
        text_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        text_widget = tk.Text(
            text_frame,
            wrap=tk.WORD,
            font=("Segoe UI", 10),
            relief="flat",
            bg=tp_window.cget("bg"),
            fg="black",
            padx=10,
            pady=10,
            height=15
        )

        # Add scrollbar
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)

        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Insert text and make read-only
        text_widget.insert("1.0", libraries_text)
        text_widget.configure(state="disabled")

        # Close button
        close_btn = ttk.Button(
            tp_frame,
            text="Close",
            command=tp_window.destroy,
            width=10
        )
        close_btn.pack(pady=(0, 0))

        # Key bindings
        tp_window.bind('<Escape>', lambda e: tp_window.destroy())
        tp_window.bind('<Return>', lambda e: tp_window.destroy())

        # Focus on close button
        close_btn.focus_set()

    @staticmethod
    def _create_copyright_section(parent) -> None:
        """Create the copyright section."""
        copyright_text = "© 2025 Aymen Brahim Djelloul. All rights reserved."

        copyright_label = ttk.Label(
            parent,
            text=copyright_text,
            font=("Segoe UI", 8),
            foreground="gray"
        )
        copyright_label.pack(pady=(0, 0))

    def _on_closing(self) -> None:
        """Handle window closing."""
        self.stop_updates()
        self.root.quit()
        self.root.destroy()


class Updater:
    """Updater class contains the logic to check for new updates from GitHub releases"""

    repo_owner: str = batterypy._AUTHOR.replace(" ", "").lower()
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
    cache_file: Path = Path(".cache") / "update_cache.json"
    cache_expiry_hours: int = 24

    def __init__(self, dev_mode: bool = True) -> None:

        # Declare constants
        self.dev_mode = dev_mode

        # Define requests session
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

            latest_version = latest_info.get('VERSION', '').lstrip('v')
            current_version = batterypy.VERSION

            # Simple VERSION comparison (you might want to use semantic versioning)
            return self._compare_versions(current_version, latest_version)

        except Exception as e:

            if self.dev_mode:
                print(f"Error checking for updates: {e}")
            return None

    def get_update_info(self) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about the latest release

        Returns:
            Dictionary with the VERSION, description, download_size_mb, download_url
        """
        try:
            return self._get_latest_release_info()

        except Exception as e:

            if self.dev_mode:
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

    def _request_latest_release(self) -> Optional:
        """Make HTTP request to GitHub API for the latest release"""
        try:
            response: Optional = self.r_session.get(
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

            if self.dev_mode:
                print("Request timed out")
            return None

        except requests.exceptions.ConnectionError:

            if self.dev_mode:
                print("Connection error occurred")
            return None

        except Exception as e:

            if self.dev_mode:
                print(f"Request error: {e}")
            return None

    def _parse_latest_release(self, response: Optional) -> Optional[Dict[str, Any]]:
        """Parse the GitHub latest release JSON response"""
        try:
            data: Optional = response.json()

            # Extract the main information
            version: str = data.get('tag_name', '')
            description: str = data.get('body', 'No description available')
            published_at: str = data.get('published_at', '')
            html_url: str = data.get('html_url', '')

            # Get download information from assets
            assets = data.get('assets', [])
            download_info: Optional = self._extract_download_info(assets)

            if not download_info:
                print("No valid installer asset found")
                return None

            parsed_info: dict[str, str] = {
                'VERSION': version,
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
    def _extract_download_info(assets: list) -> Optional[Dict[str, Any]]:
        """Extract download information from release assets, selecting the asset ending with 'installer'"""
        for asset in assets:
            name = asset.get('name', '').lower()
            if name.endswith('installer.exe'):
                size_bytes = asset.get('size', 0)
                return {
                    'asset_name': asset.get('name', ''),
                    'download_url': asset.get('browser_download_url', ''),
                    'size_mb': f"{size_bytes / (1024 * 1024):.2f} MB"
                }
        return None

    @staticmethod
    def _compare_versions(current: str, latest: str) -> bool:
        """
        Simple VERSION comparison
        For production, consider using packaging.VERSION for semantic versioning
        """
        try:
            # Remove 'v' prefix if present and split by dots
            current_parts = [int(x) for x in current.replace('v', '').split('.')]
            latest_parts = [int(x) for x in latest.replace('v', '').split('.')]

            # Pad shorter VERSION with zeros
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
        """Save data to the cache file, creating directories if needed."""
        try:
            # Ensure the directory exists
            os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)

            # Save JSON data
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"Cache successfully saved to: {self.cache_file}")

        except Exception as e:
            print(f"Failed to save cache to {self.cache_file}: {e}")

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


def __main__() -> None:
    """ This function will start the app"""

    # Run as administrator
    _run_as_admin()

    # Run the App
    root = tk.Tk()
    BatteryPyInterface(root)

    root.mainloop()


if __name__ == "__main__":
    sys.exit(0)
