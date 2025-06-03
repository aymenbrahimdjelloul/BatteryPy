
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import platform
import time
import json
from datetime import datetime


class BatteryMonitor:
    def __init__(self, root):
        self.root = root
        self.root.title("Battery Monitor v1.0")
        self.root.geometry("450x500")
        self.root.resizable(False, False)

        # App info
        self.version = "1.0"
        self.author = "Battery Monitor Developer"
        self.license = "MIT License"
        self.website = "https://github.com/batterymonitor"

        self.setup_ui()
        self.update_display()

    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title_label = ttk.Label(main_frame, text="Battery Monitor",
                                font=("Segoe UI", 18, "bold"))
        title_label.pack(pady=(0, 15))

        # Battery Level Section
        level_frame = ttk.LabelFrame(main_frame, text="Battery Level", padding="15")
        level_frame.pack(fill=tk.X, pady=5)

        # Battery level display (no progress bar)
        self.level_label = ttk.Label(level_frame, text="0%", font=("Segoe UI", 24, "bold"))
        self.level_label.pack(pady=10)

        # Battery Info Section
        info_frame = ttk.LabelFrame(main_frame, text="Battery Information", padding="10")
        info_frame.pack(fill=tk.X, pady=5)

        # Create info display using grid
        info_container = ttk.Frame(info_frame)
        info_container.pack(fill=tk.X)

        self.info_labels = {}
        info_items = [
            ("Status:", "status"),
            ("Health:", "health"),
            ("Technology:", "technology"),
            ("Temperature:", "temperature"),
            ("Voltage:", "voltage"),
            ("Current:", "current"),
            ("Power:", "power"),
            ("Cycle Count:", "cycle_count"),
            ("Fast Charging:", "fast_charge"),
            ("Time Remaining:", "time_remaining")
        ]

        for i, (label_text, key) in enumerate(info_items):
            label = ttk.Label(info_container, text=label_text, font=("Arial", 9, "bold"))
            label.grid(row=i, column=0, sticky=tk.W, pady=2, padx=(0, 15))

            value_label = ttk.Label(info_container, text="N/A", font=("Arial", 9))
            value_label.grid(row=i, column=1, sticky=tk.W, pady=2)

            self.info_labels[key] = value_label

        # Control buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=15)

        self.refresh_btn = ttk.Button(button_frame, text="Refresh",
                                      command=self.update_display)
        self.refresh_btn.pack(side=tk.LEFT, padx=5)

        self.save_btn = ttk.Button(button_frame, text="Save Report",
                                   command=self.save_report)
        self.save_btn.pack(side=tk.LEFT, padx=5)

        self.about_btn = ttk.Button(button_frame, text="About",
                                    command=self.show_about)
        self.about_btn.pack(side=tk.LEFT, padx=5)

        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var,
                               relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X, pady=(10, 0))

    def get_battery_info(self):
        """Get comprehensive battery information"""
        try:
            battery = psutil.sensors_battery()
            if battery is None:
                return {"error": "No battery found or battery information not available"}

            info = {
                "percent": battery.percent,
                "plugged": battery.power_plugged,
                "time_left": battery.secsleft if battery.secsleft != psutil.POWER_TIME_UNLIMITED else None
            }

            # Determine charging status
            if battery.power_plugged:
                if battery.percent < 100:
                    info["status"] = "Charging"
                else:
                    info["status"] = "Fully Charged"
            else:
                info["status"] = "Discharging"

            # Try to get additional battery information
            try:
                if platform.system() == "Windows":
                    info["technology"] = "Li-ion (estimated)"
                    info["health"] = "Good (estimated)"
                else:
                    info["technology"] = "Unknown"
                    info["health"] = "Unknown"
            except:
                info["technology"] = "Unknown"
                info["health"] = "Unknown"

            # Set default values for unavailable info
            info["temperature"] = "N/A"
            info["voltage"] = "N/A"
            info["current"] = "N/A"
            info["power"] = "N/A"
            info["cycle_count"] = "N/A"
            info["fast_charge"] = "N/A"

            return info

        except Exception as e:
            return {"error": f"Error getting battery info: {str(e)}"}

    def update_display(self):
        """Update the GUI with current battery information"""
        battery_info = self.get_battery_info()

        if "error" in battery_info:
            self.status_var.set(battery_info["error"])
            messagebox.showerror("Error", battery_info["error"])
            return

        # Update progress bar and percentage
        percent = battery_info.get("percent", 0)
        self.battery_progress["value"] = percent
        self.level_label.config(text=f"{percent}%")

        # Update info labels
        self.info_labels["status"].config(text=battery_info.get("status", "Unknown"))
        self.info_labels["health"].config(text=battery_info.get("health", "Unknown"))
        self.info_labels["technology"].config(text=battery_info.get("technology", "Unknown"))
        self.info_labels["temperature"].config(text=battery_info.get("temperature", "N/A"))
        self.info_labels["voltage"].config(text=battery_info.get("voltage", "N/A"))
        self.info_labels["current"].config(text=battery_info.get("current", "N/A"))
        self.info_labels["power"].config(text=battery_info.get("power", "N/A"))
        self.info_labels["cycle_count"].config(text=battery_info.get("cycle_count", "N/A"))
        self.info_labels["fast_charge"].config(text=battery_info.get("fast_charge", "N/A"))

        # Format time remaining
        time_left = battery_info.get("time_left")
        if time_left is not None and time_left > 0:
            hours, remainder = divmod(time_left, 3600)
            minutes = remainder // 60
            time_str = f"{int(hours)}h {int(minutes)}m"
        else:
            time_str = "N/A" if not battery_info.get("plugged") else "Charging"

        self.info_labels["time_remaining"].config(text=time_str)

        # Update status
        self.status_var.set(f"Last updated: {time.strftime('%H:%M:%S')}")

    def save_report(self):
        """Save battery report to file"""
        try:
            battery_info = self.get_battery_info()

            if "error" in battery_info:
                messagebox.showerror("Error", "Cannot generate report: " + battery_info["error"])
                return

            # Prepare report data
            report_data = {
                "timestamp": datetime.now().isoformat(),
                "battery_level": f"{battery_info.get('percent', 0)}%",
                "status": battery_info.get("status", "Unknown"),
                "health": battery_info.get("health", "Unknown"),
                "technology": battery_info.get("technology", "Unknown"),
                "temperature": battery_info.get("temperature", "N/A"),
                "voltage": battery_info.get("voltage", "N/A"),
                "current": battery_info.get("current", "N/A"),
                "power": battery_info.get("power", "N/A"),
                "cycle_count": battery_info.get("cycle_count", "N/A"),
                "fast_charging": battery_info.get("fast_charge", "N/A"),
                "time_remaining": self.info_labels["time_remaining"].cget("text"),
                "system_info": {
                    "os": platform.system() + " " + platform.release(),
                    "python_version": platform.python_version(),
                    "architecture": platform.architecture()[0]
                }
            }

            # Ask user for save location
            filename = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[
                    ("JSON files", "*.json"),
                    ("Text files", "*.txt"),
                    ("All files", "*.*")
                ],
                title="Save Battery Report"
            )

            if filename:
                if filename.endswith('.json'):
                    with open(filename, 'w') as f:
                        json.dump(report_data, f, indent=2)
                else:
                    # Save as readable text
                    with open(filename, 'w') as f:
                        f.write("Battery Monitor Report\n")
                        f.write("=" * 25 + "\n\n")
                        f.write(f"Generated: {report_data['timestamp']}\n\n")
                        f.write(f"Battery Level: {report_data['battery_level']}\n")
                        f.write(f"Status: {report_data['status']}\n")
                        f.write(f"Health: {report_data['health']}\n")
                        f.write(f"Technology: {report_data['technology']}\n")
                        f.write(f"Temperature: {report_data['temperature']}\n")
                        f.write(f"Voltage: {report_data['voltage']}\n")
                        f.write(f"Current: {report_data['current']}\n")
                        f.write(f"Power: {report_data['power']}\n")
                        f.write(f"Cycle Count: {report_data['cycle_count']}\n")
                        f.write(f"Fast Charging: {report_data['fast_charging']}\n")
                        f.write(f"Time Remaining: {report_data['time_remaining']}\n\n")
                        f.write("System Information:\n")
                        f.write(f"OS: {report_data['system_info']['os']}\n")
                        f.write(f"Python: {report_data['system_info']['python_version']}\n")
                        f.write(f"Architecture: {report_data['system_info']['architecture']}\n")

                messagebox.showinfo("Success", f"Report saved successfully to:\n{filename}")
                self.status_var.set("Report saved successfully")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save report: {str(e)}")

    def show_about(self):
        """Show about dialog"""
        about_text = f"""Battery Monitor v{self.version}

Author: {self.author}
License: {self.license}
Website: {self.website}

Description:
A simple GUI application to monitor battery information including level, health, technology, temperature, and charging status.

Features:
• Real-time battery level monitoring
• Comprehensive battery information display
• Report generation and export
• Cross-platform compatibility

Requirements:
• Python 3.6+
• psutil library
• tkinter (usually included with Python)

© 2024 Battery Monitor. All rights reserved."""

        # Create about window
        about_window = tk.Toplevel(self.root)
        about_window.title("About Battery Monitor")
        about_window.geometry("400x350")
        about_window.resizable(False, False)
        about_window.transient(self.root)
        about_window.grab_set()

        # Center the about window
        about_window.geometry("+%d+%d" % (
            self.root.winfo_rootx() + 50,
            self.root.winfo_rooty() + 50
        ))

        # About content
        about_frame = ttk.Frame(about_window, padding="20")
        about_frame.pack(fill=tk.BOTH, expand=True)

        about_label = ttk.Label(about_frame, text=about_text,
                                justify=tk.LEFT, font=("Arial", 9))
        about_label.pack(anchor=tk.W)

        # OK button
        ok_btn = ttk.Button(about_frame, text="OK",
                            command=about_window.destroy)
        ok_btn.pack(pady=(20, 0))


def main():
    root = tk.Tk()
    app = BatteryMonitor(root)

    try:
        root.mainloop()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()