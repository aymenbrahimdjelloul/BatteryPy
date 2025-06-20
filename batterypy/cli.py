#!/usr/bin/env python3

"""
This code or file is part of 'BatteryPy' project
copyright (c) 2023-2025 , Aymen Brahim Djelloul, All rights reserved.
use of this source code is governed by MIT License that can be found on the project folder.

    // BatteryPy - A sophisticated tool and pure python library for monitoring and reporting battery information
    // This code uses BatteryPy to collect battery data and displays it with rich color formatting.
    // It features interactive commands, beautifully aligned output, and options to save reports.

@_AUTHOR : Aymen Brahim Djelloul
VERSION : 1.5
date : 19.06.2025
License : MIT License

"""

# IMPORTS
import re
import os
import sys
import json
import shutil
import argparse
import datetime
from time import sleep
from typing import Any

# Handle missing imports
try:
    import batterypy

    from batterypy import BatteryPyException
    # use colorama for the best coloring
    from colorama import Fore, Style, init

    # Initialize colorama
    init(autoreset=True)

    class Colors:
        """
        A utility class that defines CLI coloring using 'colorama'
        """

        UNDERLINE: int = Style.BRIGHT
        YELLOW: int = Fore.YELLOW
        GREEN: int = Fore.GREEN
        RED: int = Fore.RED
        CYAN: int = Fore.CYAN
        BLUE: int = Fore.BLUE
        BOLD: int = Style.NORMAL
        END: int = Style.RESET_ALL

except ImportError:

    # Set colorama None
    colorama = None

    # Fallback with traditional ANSI color codes
    class Colors:
        """
        A utility class that defines ANSI escape sequences for styling terminal text output.
        """

        BLUE: str = "\033[94m"
        CYAN: str = "\033[96m"
        GREEN: str = "\033[92m"
        YELLOW: str = "\033[93m"
        RED: str = "\033[91m"
        BOLD: str = "\033[1m"
        UNDERLINE: str = "\033[4m"
        END: str = "\033[0m"


except BatteryPyException:
    print("\n BatteryPy cannot detect any battery. \n ")
    input("Press enter to exit...")

    # Exit the app
    sys.exit(1)


class BatteryCLI:
    """Interactive CLI tool for displaying and saving battery information"""

    def __init__(self) -> None:

        # Create BatteryPy object class
        self.battery = batterypy.Battery()

        # Get all battery info
        self.battery_info: dict = self.battery.get_result()
        # Get arguments
        self.args = self._parse_arguments()

        self.running: bool = True

        # Initialize terminal width
        self.terminal_width: int = self._get_terminal_width()

    @staticmethod
    def _get_terminal_width() -> int:
        """Get the current terminal width"""
        try:
            terminal_size = shutil.get_terminal_size()
            return terminal_size.columns

        except (AttributeError, OSError):
            return 80  # Default width if unable to determine

    @staticmethod
    def _parse_arguments() -> argparse.Namespace:
        """Parse command line arguments"""

        parser = argparse.ArgumentParser(
            description=f"{batterypy._CAPTION} - Battery Information Monitoring Tool",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )

        parser.add_argument(
            "-i", "--interactive",
            action="store_true",
            help="Run in interactive mode with command prompt"
        )

        parser.add_argument(
            "-s", "--save",
            action="store_true",
            help="Save battery information report"
        )

        parser.add_argument(
            "-f", "--format",
            choices=["text", "json", "both"],
            default="both",
            help="Format for saving the report (text, json, or both)"
        )

        parser.add_argument(
            "-o", "--output-dir",
            type=str,
            default="reports",
            help="Directory for saving reports"
        )

        parser.add_argument(
            "-v", "--VERSION",
            action="store_true",
            help="Show application VERSION"
        )

        parser.add_argument(
            "-r", "--refresh",
            type=int,
            default=0,
            help="Auto-refresh interval in seconds (0 to disable)"
        )

        return parser.parse_args()

    def run(self) -> None:
        """Run the CLI tool based on provided arguments"""
        # Handle VERSION flag first
        if self.args.VERSION:
            self._display_version()
            return

        # Always run in interactive mode unless explicitly displaying the VERSION only
        self.args.interactive = True

        # Display initial battery info
        self._refresh_battery_info()

        # Save reports if requested
        if self.args.save:
            self._save_reports()

        # Enter interactive mode if requested
        if self.args.interactive:
            self._run_interactive_mode()

    def _refresh_battery_info(self) -> None:
        """Refresh battery information and display it"""

        self.battery_info = self.battery.get_result()
        self._clear_screen()
        self._display_header()
        self._display_battery_info()

    @staticmethod
    def _clear_screen() -> None:
        """Clear the terminal screen"""
        os.system('cls' if os.name == 'nt' else 'clear')

    @staticmethod
    def _set_terminal_title() -> None:
        """ This method will set title for terminal window"""

        try:
            os.system(f"title {batterypy._CAPTION}" if batterypy._PLATFORM == "win32" else
                      f'echo -ne "\033]0;{batterypy._CAPTION}\007"')
            return None

        except OSError:
            return None

    @staticmethod
    def _get_battery_health_color(health_percent: float) -> str:
        """Return appropriate color code based on battery health percentage"""

        if health_percent >= 80:
            return Colors.GREEN
        elif health_percent >= 50:
            return Colors.YELLOW
        else:
            return Colors.RED

    @staticmethod
    def _get_battery_level_color(level_percent: float) -> str:
        """Return appropriate color code based on battery level percentage"""

        if level_percent >= 80:
            return Colors.GREEN
        elif level_percent >= 30:
            return Colors.YELLOW
        elif level_percent >= 15:
            return Colors.RED
        else:
            return f"{Colors.RED}{Colors.BOLD}"

    @staticmethod
    def _strip_ansi(text: str) -> str:
        """Remove ANSI escape codes from a string."""
        return re.sub(r'\x1B[@-_][0-?]*[ -/]*[@-~]', '', text)

    def _center_text(self, text: str) -> str:
        """Center text considering ANSI codes."""

        plain_text = self._strip_ansi(text)
        padding = max(0, (self.terminal_width - len(plain_text)) // 2)
        return f"{' ' * padding}{text}"

    def _display_header(self) -> None:
        """Display application header with VERSION and _AUTHOR info."""

        print(f""
              f"\n{Colors.BOLD}{Colors.CYAN}"
              f"{self._center_text(f'{batterypy._CAPTION} - Developed by {batterypy._AUTHOR}')}\n"
              f"{self._center_text(f'visit : {batterypy._WEBSITE}')}\n")

        print(f"{Colors.BLUE}{Colors.BOLD}{'─' * self.terminal_width}{Colors.END}\n")

    @staticmethod
    def _display_version() -> None:
        """Display detailed VERSION information"""
        print(f"\n {Colors.BOLD}Version      : {Colors.END}    {Colors.CYAN}{batterypy.VERSION}{Colors.END}")
        print(f" {Colors.BOLD}Developed by : {Colors.END}    {batterypy._AUTHOR}")
        print(f" {Colors.BOLD}Website      : {Colors.END}    {batterypy._WEBSITE}")

    @staticmethod
    def _format_info_line(label: str, value: Any, color_code: str = "") -> str:
        """Format an information line with aligned columns"""

        # Width for label column (consistent width for alignment)
        label_width = 20

        # Apply formatting if color code provided
        if color_code:
            formatted_value = f"{color_code}{value}{Colors.END}"
        else:
            formatted_value = str(value)

        return f"{Colors.BOLD}{label + ':':.<{label_width}}{Colors.END}         {formatted_value}"

    def _display_battery_info(self) -> None:
        """Display battery information with color formatting and aligned columns"""

        info = self.battery_info

        # Display additional information if not in minimal mode

        # Sort keys for consistent display
        sorted_keys = sorted([k for k in info.keys()
                              if k not in ["level", "health", "is_charging", "time_remaining"]])

        for key in sorted_keys:

            label: str = key.replace('_', ' ').title()
            value: str = info[key]

            if value is bool:
                print("work")
                # Check for booleans
                if value == "True":
                    value = "Yes"
                elif value == "False":
                    value = "No"

            print(f"{self._format_info_line(label, value)}")

        # Bottom information line
        print(f"\n{Colors.BLUE}{Colors.BOLD}{'─' * self.terminal_width}{Colors.END}")
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"{Colors.BLUE}Last updated: {timestamp}{Colors.END}")

        # Always display simplified command help, even without interactive mode
        self._display_simplified_command_help()

    @staticmethod
    def _display_simplified_command_help() -> None:
        """Display simplified command help for quick reference"""

        print(f"{Colors.GREEN}[r]{Colors.END} refresh | ", end="")
        print(f"{Colors.GREEN}[s]{Colors.END} save report | ", end="")
        print(f"{Colors.GREEN}[q]{Colors.END} quit")

    @staticmethod
    def _display_command_help() -> None:
        """Display available commands for interactive mode"""

        commands: list = [
            ("refresh (r)", "Refresh battery information"),
            ("save (s)", "Save battery report"),
            ("clear (c)", "Clear the screen"),
            ("quit ('q' or 'exit' or 'bye')", "Exit the application"),
            ("help ('?' or 'help' or 'h')", "Show this help"),
            ("VERSION ('VERSION' or 'v')", "Show BatteryPy current VERSION")
        ]

        print(f"\n{Colors.YELLOW}{Colors.BOLD}Available Commands:{Colors.END}")

        # Calculate maximum command length for alignment
        max_cmd_len: int = max(len(cmd[0]) for cmd in commands)

        for cmd, desc in commands:
            print(f"  {Colors.GREEN}{cmd.ljust(max_cmd_len)}{Colors.END}  {desc}")

    @staticmethod
    def _wait_user_input() -> None:
        """ This method will wait for user input"""
        input(f"\n{Colors.CYAN}Press any key to continue...{Colors.END}")
        # wait
        sleep(0.5)

    @staticmethod
    def _get_user_input() -> str:
        """ This method will wait for user input"""
        return str(input("> :"))

    def _run_interactive_mode(self) -> None:
        """Run the application in interactive mode with command prompt"""
        self.running = True

        # Set terminal windows title
        self._set_terminal_title()

        while self.running:
            try:
                user_input = self._get_user_input().lower()

                # Handle single-key commands first
                if user_input in ("q", "quit", "exit", "bye"):
                    self.running = False
                    print(f"{Colors.YELLOW}Exiting {batterypy._CAPTION}...{Colors.END}")

                    # wait
                    sleep(2)
                    # exit
                    sys.exit(0)

                elif user_input in ('r', 'refresh'):
                    self._refresh_battery_info()

                elif user_input in ('s', 'save'):
                    self._save_reports()
                    self._wait_user_input()

                    self._refresh_battery_info()

                elif user_input == 'c':
                    self._refresh_battery_info()

                elif user_input in ('v', 'VERSION'):
                    self._display_version()
                    # Wait for user input
                    self._wait_user_input()

                    self._refresh_battery_info()

                elif user_input in ('h', '?', 'help'):

                    # print out help
                    self._display_command_help()
                    # Wait for user input
                    self._wait_user_input()

                    self._refresh_battery_info()

                else:
                    # Only show "unknown command" for longer inputs, not single keys
                    if len(user_input) > 1:
                        print(f"{Colors.RED}Unknown command: {user_input}\n"
                              f"{Colors.RED} try using '?' or 'help' {Colors.END}")

                    else:
                        print(f"{Colors.RED} Invalid input, use '?' or 'help' .")

                    sleep(2)
                    self._refresh_battery_info()

            except KeyboardInterrupt:
                self.running = False
                print(f"\n{Colors.YELLOW}Battery monitoring terminated.{Colors.END}")
                break

            except EOFError:
                self.running = False
                print(f"\n{Colors.YELLOW}Input stream closed. Exiting.{Colors.END}")

                break

    def _format_text_report(self) -> str:
        """Format battery information as the text report"""

        info: dict = self.battery_info
        report: list = []
        width: int = 60  # Width for the report box

        # Header
        report.append("=" * width)
        report.append(f"{batterypy._CAPTION} - Battery Report".center(width))
        report.append("-" * width)
        report.append(f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("=" * width)
        report.append("")

        # Battery information
        report.append("BATTERY STATUS SUMMARY".center(width))
        report.append("-" * width)

        # Format key information with aligned values
        label_width = 25
        report.append(f"{'Battery Level:':<{label_width}} {info.get('level', 0)}%")
        report.append(f"{'Battery Health:':<{label_width}} {info.get('health', 0)}%")
        report.append(f"{'Status:':<{label_width}} {'Charging' if info.get('is_charging', False) else 'Discharging'}")
        report.append(f"{'Time Remaining:':<{label_width}} {info.get('time_remaining', 'Unknown')}")

        report.append("")
        report.append("DETAILED INFORMATION".center(width))
        report.append("-" * width)

        # Add all other information, sorted alphabetically
        sorted_keys: list = sorted([k for k in info.keys()
                                    if k not in ["level", "health", "is_charging", "time_remaining"]])

        for key in sorted_keys:
            label = key.replace('_', ' ').title()
            report.append(f"{label + ':':<{label_width}} {info[key]}")

        # Footer
        report.append("")
        report.append("=" * width)
        report.append(f"Report by {batterypy._CAPTION}".center(width))
        report.append(f"{batterypy._WEBSITE}".center(width))

        return "\n".join(report)

    def _save_reports(self) -> None:
        """Save battery information reports in specified formats"""

        timestamp: str = datetime.datetime.now().strftime("%Y%m%d_%H%M")

        # Create output directory if it doesn't exist
        os.makedirs(self.args.output_dir, exist_ok=True)

        formats: list = []
        if self.args.format in ["text", "both"]:
            formats.append("text")
        if self.args.format in ["json", "both"]:
            formats.append("json")

        saved_files: list = []

        for fmt in formats:
            if fmt == "text":
                filepath = os.path.join(self.args.output_dir, f"battery_report_{timestamp}.txt")
                with open(filepath, "w") as f:
                    f.write(self._format_text_report())
                saved_files.append(("Text report", filepath))

            elif fmt == "json":
                filepath = os.path.join(self.args.output_dir, f"battery_report_{timestamp}.json")
                report_data: dict = {
                    "generated_by": f"{batterypy._CAPTION}",
                    "batterypy_version": batterypy.VERSION,
                    "timestamp": datetime.datetime.now().isoformat(),
                    "battery_info": self.battery_info
                }

                with open(filepath, "w") as f:
                    json.dump(report_data, f, indent=2)
                saved_files.append(("JSON report", filepath))

        # Display save confirmation
        if saved_files:
            print(f"\n{Colors.GREEN}{Colors.BOLD}Reports saved successfully:{Colors.END}")
            for report_type, path in saved_files:
                print(f"  {Colors.GREEN}✓ {report_type}: {path}{Colors.END}")


def __main__() -> int:
    """Main function to run the CLI tool"""

    try:
        cli = BatteryCLI()
        cli.run()
        return 0

    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Battery information gathering interrupted.{Colors.END}")
        return 0

    except BatteryPyException:

        print(f"\n\n  {Colors.YELLOW}{batterypy._CAPTION} ⚠️  No battery detected. Battery monitoring "
              f"is unavailable on this device.{Colors.END}\n")

        input("  Press Enter to exit.")
        return 1


if __name__ == "__main__":
    sys.exit(0)
