import os
import sys
import logging
import threading
import json
import pkg_resources
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, simpledialog

from youtube_bulk_upload import YouTubeBulkUpload


class YouTubeBulkUploaderGUI:
    def __init__(self, gui_root: tk.Tk, logger: logging.Logger, bundle_dir: Path, running_in_pyinstaller: bool):
        self.logger = logger
        self.logger.debug(f"Initializing YouTubeBulkUploaderGUI, bundle_dir: {bundle_dir}")

        self.gui_root = gui_root
        self.bundle_dir = bundle_dir
        self.running_in_pyinstaller = running_in_pyinstaller

        # Define variables for inputs
        self.log_level = logging.DEBUG
        self.log_level_var = tk.StringVar(value="info")
        self.log_level_var.trace("w", self.on_log_level_change)

        self.upload_thread = None
        self.stop_event = threading.Event()

        self.dry_run_var = tk.BooleanVar(value=True)
        self.noninteractive_var = tk.BooleanVar()
        self.source_directory_var = tk.StringVar(value=os.path.expanduser("~"))

        self.yt_client_secrets_file_var = tk.StringVar(value="client_secret.json")
        self.upload_batch_limit_var = tk.IntVar(value=100)
        self.input_file_extensions_var = tk.StringVar(value=".mp4 .mov")
        self.yt_category_id_var = tk.StringVar(value="10")
        self.yt_keywords_var = tk.StringVar(value="music")
        self.yt_desc_template_file_var = tk.StringVar()
        self.yt_title_prefix_var = tk.StringVar()
        self.yt_title_suffix_var = tk.StringVar()
        self.thumb_file_prefix_var = tk.StringVar()
        self.thumb_file_suffix_var = tk.StringVar()
        self.thumb_file_extensions_var = tk.StringVar(value=".png .jpg .jpeg")
        self.dont_show_welcome_message_var = tk.BooleanVar(value=False)

        # Fire off our clean shutdown function when the user requests to close the window
        gui_root.wm_protocol("WM_DELETE_WINDOW", self.on_closing)

        # Set the application icon to the YouTube Bulk Upload logo
        self.set_window_icon()

        # Set up the GUI frames and widgets
        self.create_gui_frames_widgets()

        # Add a text box to the GUI which shows all log messages using the existing shared logger
        self.add_textbox_log_handler()

        # Ensure the window is updated with the latest UI changes before calculating the minimum size
        self.gui_root.update()
        self.gui_root.minsize(self.gui_root.winfo_width(), self.gui_root.winfo_height())

        # Load user GUI config values on initialization
        user_home_dir = os.path.expanduser("~")
        self.gui_config_filepath = os.path.join(user_home_dir, "youtube_bulk_upload_config.json")
        self.load_gui_config_options()

        # Show the welcome popup if applicable
        self.show_welcome_popup()

        self.user_input_event = threading.Event()
        self.user_input_result = None

        self.logger.info("YouTubeBulkUploaderGUI Initialized")

    def show_welcome_popup(self):
        # Don't show the popup if the user opted out
        if self.dont_show_welcome_message_var.get():
            return

        welcome_window = tk.Toplevel(self.gui_root)
        welcome_window.title("Welcome to YouTube Bulk Uploader")

        message = """Welcome to YouTube Bulk Uploader!

This tool helps you upload videos to YouTube in bulk with custom metadata derived from the video file names.

To use it, you'll need a YouTube Data API Client Secret (JSON file) - reach out to Andrew if you aren't sure where to get this!

Once you have that, you can point this tool at a directory of video files and it will upload them to YouTube, generating titles based on the filename, setting descriptions based on a template file, and optionally using a dedicated thumbnail image for each video in the same directory.

I highly recommend testing it out with "Dry Run" enabled first, in which mode it will log exactly what it is doing but won't actually upload anything.

Once you have confidence that your settings are correct and you're ready to execute it in bulk on a large number of files, tick the "Non-interactive" checkbox and it will no longer prompt you with popups asking for confirmation.

The find/replace patterns for video titles, thumbnail filenames, and YouTube descriptions all support regular expressions and empty replacement strings, or they can be left blank if you don't need to use them.

Hover over any element in the user interface for a tooltip popup explanation of that functionality.

Click the "Watch Tutorial" button below to watch the tutorial video before trying to use it!

Happy uploading!
-Andrew <andrew@beveridge.uk>"""

        tk.Label(welcome_window, text=message, wraplength=600, justify="left").pack(padx=20, pady=10)

        dont_show_again = tk.Checkbutton(welcome_window, text="Don't show this message again", variable=self.dont_show_welcome_message_var)
        dont_show_again.pack()
        button_frame = tk.Frame(welcome_window)
        button_frame.pack(pady=10)

        video_button = tk.Button(
            button_frame, text="Watch Tutorial", command=lambda: self.open_link("https://youtu.be/9WklrdupZhg")
        )
        video_button.pack(side=tk.LEFT, padx=5)

        close_button = tk.Button(button_frame, text="Close", command=welcome_window.destroy)
        close_button.pack(side=tk.LEFT, padx=5)
        # Update the window to calculate its size
        welcome_window.update_idletasks()

        # Retrieve the calculated size
        welcome_window_width = welcome_window.winfo_width()
        welcome_window_height = welcome_window.winfo_height()

        # Calculate the center position
        position_right = int(self.gui_root.winfo_x() + (self.gui_root.winfo_width() / 2) - (welcome_window_width / 2))
        position_down = int(self.gui_root.winfo_y() + (self.gui_root.winfo_height() / 2) - (welcome_window_height / 2))

        # Position the window in the center of the parent window
        welcome_window.geometry(f"+{position_right}+{position_down}")

    def open_link(self, url):
        import webbrowser

        webbrowser.open(url)

    def load_gui_config_options(self):
        self.logger.info(f"Loading GUI configuration values from file: {self.gui_config_filepath}")

        try:
            with open(self.gui_config_filepath, "r") as f:
                config = json.load(f)
                # Set the variables' values from the config file
                self.log_level_var.set(config.get("log_level", "info"))
                self.dry_run_var.set(config.get("dry_run", True))
                self.noninteractive_var.set(config.get("noninteractive", False))
                self.source_directory_var.set(config.get("source_directory", os.path.expanduser("~")))
                self.yt_client_secrets_file_var.set(config.get("yt_client_secrets_file", "client_secret.json"))
                self.upload_batch_limit_var.set(config.get("upload_batch_limit", 100))
                self.input_file_extensions_var.set(config.get("input_file_extensions", ".mp4 .mov"))
                self.yt_category_id_var.set(config.get("yt_category_id", "10"))
                self.yt_keywords_var.set(config.get("yt_keywords", "music"))
                self.yt_desc_template_file_var.set(config.get("yt_desc_template_file", ""))
                self.yt_title_prefix_var.set(config.get("yt_title_prefix", ""))
                self.yt_title_suffix_var.set(config.get("yt_title_suffix", ""))
                self.thumb_file_prefix_var.set(config.get("thumb_file_prefix", ""))
                self.thumb_file_suffix_var.set(config.get("thumb_file_suffix", ""))
                self.thumb_file_extensions_var.set(config.get("thumb_file_extensions", ".png .jpg .jpeg"))
                self.dont_show_welcome_message_var = tk.BooleanVar(value=config.get("dont_show_welcome_message", False))

                # Load replacement patterns
                youtube_description_replacements = config.get("youtube_description_replacements", [])
                youtube_title_replacements = config.get("youtube_title_replacements", [])
                thumbnail_filename_replacements = config.get("thumbnail_filename_replacements", [])

                # Populate the Listbox widgets with the loaded replacements
                for find, replace in youtube_description_replacements:
                    self.youtube_desc_frame.replacements_listbox.insert(tk.END, f"{find} -> {replace}")
                for find, replace in youtube_title_replacements:
                    self.youtube_title_frame.replacements_listbox.insert(tk.END, f"{find} -> {replace}")
                for find, replace in thumbnail_filename_replacements:
                    self.thumbnail_frame.replacements_listbox.insert(tk.END, f"{find} -> {replace}")

        except FileNotFoundError:
            pass  # If the config file does not exist, just pass

    def save_gui_config_options(self):
        self.logger.info(f"Saving GUI configuration values to file: {self.gui_config_filepath}")

        # Serialize replacement patterns
        youtube_description_replacements = self.youtube_desc_frame.get_replacements()
        youtube_title_replacements = self.youtube_title_frame.get_replacements()
        thumbnail_filename_replacements = self.thumbnail_frame.get_replacements()

        config = {
            "log_level": self.log_level_var.get(),
            "dry_run": self.dry_run_var.get(),
            "noninteractive": self.noninteractive_var.get(),
            "source_directory": self.source_directory_var.get(),
            "yt_client_secrets_file": self.yt_client_secrets_file_var.get(),
            "input_file_extensions": self.input_file_extensions_var.get(),
            "upload_batch_limit": self.upload_batch_limit_var.get(),
            "yt_category_id": self.yt_category_id_var.get(),
            "yt_keywords": self.yt_keywords_var.get(),
            "yt_desc_template_file": self.yt_desc_template_file_var.get(),
            "yt_title_prefix": self.yt_title_prefix_var.get(),
            "yt_title_suffix": self.yt_title_suffix_var.get(),
            "thumb_file_prefix": self.thumb_file_prefix_var.get(),
            "thumb_file_suffix": self.thumb_file_suffix_var.get(),
            "thumb_file_extensions": self.thumb_file_extensions_var.get(),
            "youtube_description_replacements": youtube_description_replacements,
            "youtube_title_replacements": youtube_title_replacements,
            "thumbnail_filename_replacements": thumbnail_filename_replacements,
            "dont_show_welcome_message": self.dont_show_welcome_message_var.get(),
        }
        with open(self.gui_config_filepath, "w") as f:
            json.dump(config, f, indent=4)

    def on_log_level_change(self, *args):
        self.logger.info(f"Log level changed to: {self.log_level_var.get()}")

        # Get log level string value from GUI
        log_level_str = self.log_level_var.get()
        # Convert log level from string to logging module constant
        self.log_level = getattr(logging, log_level_str.upper(), logging.DEBUG)

        self.logger.setLevel(self.log_level)

    def create_gui_frames_widgets(self):
        self.logger.debug("Setting up GUI frames and widgets")
        self.row = 0
        # Fetch the package version
        package_version = pkg_resources.get_distribution("youtube-bulk-upload").version
        self.gui_root.title(f"YouTube Bulk Upload - v{package_version}")

        # Configure the grid layout to allow frames to resize properly
        self.gui_root.grid_rowconfigure(0, weight=1)
        self.gui_root.grid_rowconfigure(1, weight=1)
        self.gui_root.grid_columnconfigure(0, weight=1)
        self.gui_root.grid_columnconfigure(1, weight=1)

        # General Options Frame
        self.general_frame = ReusableWidgetFrame(self.gui_root, self.logger, "General Options")
        self.general_frame.grid(row=self.row, column=0, padx=10, pady=5, sticky="nsew")
        self.general_frame.grid_rowconfigure(8, weight=1)
        self.general_frame.grid_columnconfigure(1, weight=1)
        self.add_general_options_widgets()

        # YouTube Title Frame with Find/Replace
        self.youtube_title_frame = ReusableWidgetFrame(self.gui_root, self.logger, "YouTube Title Options")
        self.youtube_title_frame.grid(row=self.row, column=1, padx=10, pady=5, sticky="nsew")
        self.youtube_title_frame.grid_rowconfigure(4, weight=1)
        self.youtube_title_frame.grid_columnconfigure(1, weight=1)
        self.add_youtube_title_widgets()

        self.row += 1

        # Thumbnail Options Frame with Find/Replace
        self.thumbnail_frame = ReusableWidgetFrame(self.gui_root, self.logger, "YouTube Thumbnail Options")
        self.thumbnail_frame.grid(row=self.row, column=0, padx=10, pady=5, sticky="nsew")
        self.thumbnail_frame.grid_rowconfigure(4, weight=1)
        self.thumbnail_frame.grid_columnconfigure(1, weight=1)
        self.add_thumbnail_options_widgets()

        # YouTube Description Frame with Find/Replace
        self.youtube_desc_frame = ReusableWidgetFrame(self.gui_root, self.logger, "YouTube Description Options")
        self.youtube_desc_frame.grid(row=self.row, column=1, padx=10, pady=5, sticky="nsew")
        self.youtube_desc_frame.grid_rowconfigure(4, weight=1)
        self.youtube_desc_frame.grid_columnconfigure(1, weight=1)
        self.add_youtube_description_widgets()

        self.row += 1

        # Create a frame that spans across two columns of the main grid
        button_frame = tk.Frame(self.gui_root)
        button_frame.grid(row=self.row, column=0, columnspan=2, padx=10, pady=5, sticky="ew")

        # Configure the frame's grid to have three columns with equal weight
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)
        button_frame.grid_columnconfigure(2, weight=1)

        # Place the buttons inside the frame, each in its own column
        self.run_button = tk.Button(button_frame, text="Run", command=self.run_upload)
        self.run_button.grid(row=0, column=0, sticky="ew")
        Tooltip(
            self.run_button, "Starts the process of uploading videos! Please ensure you have tested your settings in Dry Run mode first!"
        )

        self.stop_button = tk.Button(button_frame, text="Stop", command=self.stop_operation)
        self.stop_button.grid(row=0, column=1, sticky="ew")
        Tooltip(self.stop_button, "Stops the current operation, if running.")

        self.clear_log_button = tk.Button(button_frame, text="Clear Log", command=self.clear_log)
        self.clear_log_button.grid(row=0, column=2, sticky="ew")
        Tooltip(self.clear_log_button, "Clears the log output below.")

        self.row += 1

        # Log output at the bottom spanning both columns
        log_output_label = tk.Label(self.gui_root, text="Log Output:")
        log_output_label.grid(row=self.row, column=0, columnspan=2, sticky="w")
        Tooltip(
            log_output_label,
            "Displays the log of all operations, including text replacements, successful and failed uploads. If something isn't working as expected, please read this log before asking for help.",
        )

        self.log_output = scrolledtext.ScrolledText(self.gui_root, height=10)
        self.log_output.grid(row=self.row, column=0, columnspan=2, padx=10, pady=5, sticky="nsew")
        self.log_output.config(state=tk.DISABLED)

    def add_general_options_widgets(self):
        frame = self.general_frame

        # Log Level Label with Tooltip
        log_level_label = tk.Label(self.general_frame, text="Log Level:")
        log_level_label.grid(row=frame.row, column=0, sticky="w")
        Tooltip(log_level_label, "Sets the verbosity of the application logs, which are written to the text box below and also a log file.")

        # Log Level OptionMenu with Tooltip
        log_level_option_menu = tk.OptionMenu(self.general_frame, self.log_level_var, "info", "warning", "error", "debug")
        log_level_option_menu.grid(row=frame.row, column=1, sticky="ew")
        Tooltip(log_level_option_menu, "Choose between Info, Warning, Error, or Debug log levels.")

        frame.new_row()

        dry_run_checkbutton = tk.Checkbutton(self.general_frame, text="Dry Run", variable=self.dry_run_var)
        dry_run_checkbutton.grid(row=frame.row, column=0, sticky="w")
        Tooltip(
            dry_run_checkbutton,
            "Simulates the upload process without posting videos to YouTube. Keep this enabled until you have tested your settings!",
        )

        noninteractive_checkbutton = tk.Checkbutton(self.general_frame, text="Non-interactive", variable=self.noninteractive_var)
        noninteractive_checkbutton.grid(row=frame.row, column=1, sticky="w")
        Tooltip(
            noninteractive_checkbutton,
            "Runs the upload process without manual intervention. Enable this once you've tested your settings and you're ready to bulk process!",
        )

        frame.new_row()

        source_dir_label = tk.Label(self.general_frame, text="Source Directory:")
        source_dir_label.grid(row=frame.row, column=0, sticky="w")
        Tooltip(source_dir_label, "The directory where your video files are located.")

        source_dir_entry = tk.Entry(self.general_frame, textvariable=self.source_directory_var)
        source_dir_entry.grid(row=frame.row, column=1, sticky="ew")
        source_dir_browse_button = tk.Button(self.general_frame, text="Browse...", command=self.select_source_directory)
        source_dir_browse_button.grid(row=frame.row, column=2, sticky="ew")
        Tooltip(source_dir_browse_button, "Open a dialog to select the source directory where your video files are located.")

        # YouTube Client Secrets File
        frame.new_row()

        yt_client_secrets_label = tk.Label(self.general_frame, text="YouTube Client Secret File:")
        yt_client_secrets_label.grid(row=frame.row, column=0, sticky="w")
        Tooltip(
            yt_client_secrets_label,
            "The JSON file containing your YouTube Data API client secret credentials. If you aren't sure how to get this, ask Andrew!",
        )

        yt_client_secrets_entry = tk.Entry(self.general_frame, textvariable=self.yt_client_secrets_file_var)
        yt_client_secrets_entry.grid(row=frame.row, column=1, sticky="ew")
        yt_client_secrets_browse_button = tk.Button(self.general_frame, text="Browse...", command=self.select_client_secrets_file)
        yt_client_secrets_browse_button.grid(row=frame.row, column=2, sticky="ew")
        Tooltip(yt_client_secrets_browse_button, "Open a dialog to select the YouTube client secret file.")

        # Input File Extensions
        frame.new_row()
        file_extensions_label = tk.Label(self.general_frame, text="Input File Extensions:")
        file_extensions_label.grid(row=frame.row, column=0, sticky="w")
        Tooltip(
            file_extensions_label,
            "The file extension(s) for videos you want to upload from the source folder. Separate multiple extensions with a space.",
        )

        file_extensions_entry = tk.Entry(self.general_frame, textvariable=self.input_file_extensions_var)
        file_extensions_entry.grid(row=frame.row, column=1, sticky="ew")

        # Upload Batch Limit
        frame.new_row()

        batch_limit_label = tk.Label(self.general_frame, text="Upload Batch Limit:")
        batch_limit_label.grid(row=frame.row, column=0, sticky="w")
        Tooltip(
            batch_limit_label,
            "The maximum number of videos to upload in a single batch. YouTube allows a maximum of 100 videos per 24 hour period!",
        )

        batch_limit_entry = tk.Entry(self.general_frame, textvariable=self.upload_batch_limit_var)
        batch_limit_entry.grid(row=frame.row, column=1, sticky="ew")

        # YouTube Category ID
        frame.new_row()

        yt_category_label = tk.Label(self.general_frame, text="YouTube Category ID:")
        yt_category_label.grid(row=frame.row, column=0, sticky="w")
        Tooltip(yt_category_label, "The ID of the YouTube category under which the videos will be uploaded.")

        yt_category_entry = tk.Entry(self.general_frame, textvariable=self.yt_category_id_var)
        yt_category_entry.grid(row=frame.row, column=1, sticky="ew")

        # YouTube Keywords
        frame.new_row()
        yt_keywords_label = tk.Label(self.general_frame, text="YouTube Keywords:")
        yt_keywords_label.grid(row=frame.row, column=0, sticky="w")
        Tooltip(yt_keywords_label, "Keywords to be added to the video metadata. Separate multiple keywords with a comma.")

        yt_keywords_entry = tk.Entry(self.general_frame, textvariable=self.yt_keywords_var)
        yt_keywords_entry.grid(row=frame.row, column=1, sticky="ew")

    def add_youtube_title_widgets(self):
        frame = self.youtube_title_frame

        prefix_label = tk.Label(self.youtube_title_frame, text="Prefix:")
        prefix_label.grid(row=frame.row, column=0, sticky="w")
        Tooltip(prefix_label, "Prefix to add to the beginning of the video filename to create your preferred YouTube video title.")

        prefix_entry = tk.Entry(self.youtube_title_frame, textvariable=self.yt_title_prefix_var)
        prefix_entry.grid(row=frame.row, column=1, sticky="ew")
        Tooltip(prefix_entry, "Enter the prefix text here.")

        frame.new_row()

        suffix_label = tk.Label(self.youtube_title_frame, text="Suffix:")
        suffix_label.grid(row=frame.row, column=0, sticky="w")
        Tooltip(suffix_label, "Suffix to add to the end of the video filename to create your preferred YouTube video title.")

        suffix_entry = tk.Entry(self.youtube_title_frame, textvariable=self.yt_title_suffix_var)
        suffix_entry.grid(row=frame.row, column=1, sticky="ew")
        Tooltip(suffix_entry, "Enter the suffix text here.")

        frame.new_row()
        self.youtube_title_frame.add_find_replace_widgets(
            "Find / Replace Patterns:",
            "Define regex patterns for finding and replacing text in the video filename to create your preferred YouTube video title.",
        )

    def add_youtube_description_widgets(self):
        frame = self.youtube_desc_frame

        template_file_label = tk.Label(self.youtube_desc_frame, text="Template File:")
        template_file_label.grid(row=frame.row, column=0, sticky="w")
        Tooltip(template_file_label, "Path to the template file used for YouTube video descriptions.")

        template_file_entry = tk.Entry(self.youtube_desc_frame, textvariable=self.yt_desc_template_file_var, state="readonly")
        template_file_entry.grid(row=frame.row, column=1, sticky="ew")
        Tooltip(template_file_entry, "Displays the file path of the selected template file. This field is read-only.")

        browse_button = tk.Button(self.youtube_desc_frame, text="Browse...", command=self.select_yt_desc_template_file)
        browse_button.grid(row=frame.row, column=2, sticky="ew")
        Tooltip(browse_button, "Open a dialog to select the template file for YouTube video descriptions.")

        frame.new_row()
        self.youtube_desc_frame.add_find_replace_widgets(
            "Find / Replace Patterns:",
            "Define regex patterns to find & replace text in the template to generate the desired description for each video. Use {{youtube_title}} in a replacement string to inject the video title.",
        )

    def add_thumbnail_options_widgets(self):
        frame = self.thumbnail_frame
        filename_prefix_label = tk.Label(self.thumbnail_frame, text="Filename Prefix:")
        filename_prefix_label.grid(row=frame.row, column=0, sticky="w")
        Tooltip(filename_prefix_label, "Prefix to add to the beginning of the video filename to match your thumbnail filename pattern.")

        filename_prefix_entry = tk.Entry(self.thumbnail_frame, textvariable=self.thumb_file_prefix_var)
        filename_prefix_entry.grid(row=frame.row, column=1, sticky="ew")
        Tooltip(
            filename_prefix_entry,
            "Enter the prefix for thumbnail filenames here. If not working as expected, see the log output to understand how this works.",
        )

        frame.new_row()
        filename_suffix_label = tk.Label(self.thumbnail_frame, text="Filename Suffix:")
        filename_suffix_label.grid(row=frame.row, column=0, sticky="w")
        Tooltip(filename_suffix_label, "Suffix to add to the end of the video filename to match your thumbnail filename pattern.")

        filename_suffix_entry = tk.Entry(self.thumbnail_frame, textvariable=self.thumb_file_suffix_var)
        filename_suffix_entry.grid(row=frame.row, column=1, sticky="ew")
        Tooltip(
            filename_suffix_entry,
            "Enter the suffix for thumbnail filenames here. If not working as expected, see the log output to understand how this works.",
        )

        frame.new_row()
        file_extensions_label = tk.Label(self.thumbnail_frame, text="File Extensions:")
        file_extensions_label.grid(row=frame.row, column=0, sticky="w")
        Tooltip(file_extensions_label, "Allowed file extensions for thumbnails.")

        file_extensions_entry = tk.Entry(self.thumbnail_frame, textvariable=self.thumb_file_extensions_var)
        file_extensions_entry.grid(row=frame.row, column=1, sticky="ew")
        Tooltip(file_extensions_entry, "Enter the allowed file extensions for thumbnails, separated by spaces.")

        frame.new_row()
        self.thumbnail_frame.add_find_replace_widgets(
            "Find / Replace Patterns:", "Define regex patterns for finding and replacing text in thumbnail filenames."
        )

    def set_window_icon(self):
        self.logger.info("Setting window icon to app logo")

        try:
            icon_filepaths = [
                os.path.join(self.bundle_dir, "logo.png"),
                os.path.join(self.bundle_dir, "youtube_bulk_upload", "logo.png"),
                os.path.join(self.bundle_dir, "logo.ico"),
                os.path.join(self.bundle_dir, "youtube_bulk_upload", "logo.ico"),
            ]

            icon_set = False
            for icon_filepath in icon_filepaths:
                if os.path.exists(icon_filepath):
                    self.logger.info(f"Found logo image at filepath: {icon_filepath}, setting as window icon.")
                    if icon_filepath.endswith(".ico"):
                        self.gui_root.iconbitmap(icon_filepath)
                    else:
                        photo = tk.PhotoImage(file=icon_filepath)
                        self.gui_root.wm_iconphoto(False, photo)
                    icon_set = True
                    break

            if not icon_set:
                raise FileNotFoundError("Logo image not found in any of the specified filepaths.")

        except Exception as e:
            self.logger.error(f"Failed to set window icon due to error: {e}")

    def add_textbox_log_handler(self):
        self.logger.info("Adding textbox log handler to logger")
        self.log_handler_textbox = TextHandler(self.logger, self.log_output)

        log_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(module)s - %(message)s")
        self.log_handler_textbox.setFormatter(log_formatter)

        self.logger.addHandler(self.log_handler_textbox)

    def prompt_user_bool(self, prompt_message, allow_empty=False):
        """
        Prompt the user for a boolean input via a GUI dialog in a thread-safe manner.

        :param prompt_message: The message to display in the dialog.
        :param allow_empty: Not used in this context, kept for compatibility.
        :return: The boolean value entered by the user, or None if the dialog was canceled.
        """
        self.logger.debug(f"Prompting user for boolean input")

        def prompt():
            self.user_input_result = messagebox.askyesno("Confirm", prompt_message)
            self.user_input_event.set()  # Signal that input has been received

        self.user_input_event.clear()
        self.gui_root.after(0, prompt)
        return None  # Immediate return; we'll wait for the input

    def prompt_user_text(self, prompt_message, default_response=""):
        """
        Prompt the user for text input via a GUI dialog.

        :param prompt_message: The message to display in the dialog.
        :param default_response: The default text to display in the input box.
        :return: The text entered by the user, or None if the dialog was canceled.
        """
        self.logger.debug(f"Prompting user for text input")

        def prompt():
            self.user_input_result = simpledialog.askstring("Input", prompt_message, parent=self.gui_root, initialvalue=default_response)
            self.user_input_event.set()  # Signal that input has been received

        self.user_input_event.clear()
        self.gui_root.after(0, prompt)
        return None  # Immediate return; we'll wait for the input

    def stop_operation(self):
        self.logger.info("Stopping current operation")
        self.stop_event.set()

    def run_upload(self):
        self.logger.info("Initializing YouTubeBulkUpload class with parameters from GUI")

        self.stop_event.clear()

        dry_run = self.dry_run_var.get()
        noninteractive = self.noninteractive_var.get()
        source_directory = self.source_directory_var.get()
        yt_client_secrets_file = self.yt_client_secrets_file_var.get()
        yt_category_id = self.yt_category_id_var.get()
        yt_keywords = self.yt_keywords_var.get().split()
        yt_desc_template_file = self.yt_desc_template_file_var.get() or None
        yt_title_prefix = self.yt_title_prefix_var.get()
        yt_title_suffix = self.yt_title_suffix_var.get()
        thumb_file_prefix = self.thumb_file_prefix_var.get()
        thumb_file_suffix = self.thumb_file_suffix_var.get()
        thumb_file_extensions = self.thumb_file_extensions_var.get().split()

        # Extract replacement patterns
        youtube_description_replacements = self.youtube_desc_frame.get_replacements()
        youtube_title_replacements = self.youtube_title_frame.get_replacements()
        thumbnail_filename_replacements = self.thumbnail_frame.get_replacements()

        # Initialize YouTubeBulkUpload with collected parameters and replacements
        self.youtube_bulk_upload = YouTubeBulkUpload(
            logger=self.logger,
            dry_run=dry_run,
            interactive_prompt=not noninteractive,
            stop_event=self.stop_event,
            gui=self,
            source_directory=source_directory,
            youtube_client_secrets_file=yt_client_secrets_file,
            youtube_category_id=yt_category_id,
            youtube_keywords=yt_keywords,
            youtube_description_template_file=yt_desc_template_file,
            youtube_title_prefix=yt_title_prefix,
            youtube_title_suffix=yt_title_suffix,
            thumbnail_filename_prefix=thumb_file_prefix,
            thumbnail_filename_suffix=thumb_file_suffix,
            thumbnail_filename_extensions=thumb_file_extensions,
            youtube_description_replacements=youtube_description_replacements,
            youtube_title_replacements=youtube_title_replacements,
            thumbnail_filename_replacements=thumbnail_filename_replacements,
        )

        self.logger.info("Beginning YouTubeBulkUpload process thread...")

        # Run the upload process in a separate thread to prevent GUI freezing
        self.upload_thread = threading.Thread(target=self.threaded_upload, args=(self.youtube_bulk_upload,))
        self.upload_thread.start()

    def on_closing(self):
        self.logger.info("YouTubeBulkUploaderGUI on_closing called, saving configuration and stopping upload thread")

        self.logger.debug("Setting stop_event to stop upload thread")
        self.stop_event.set()

        self.save_gui_config_options()

        # Wait for the thread to finish - bulk_upload.py has self.stop_event check in process() loop
        # so it should wait for any current upload to finish then not continue to another
        if self.upload_thread:
            self.logger.debug("Waiting for upload thread to finish")
            self.upload_thread.join()

        self.logger.info("Upload thread shut down successfully, destroying GUI window. Goodbye for now!")
        self.gui_root.destroy()

    def threaded_upload(self, youtube_bulk_upload):
        self.logger.debug("Starting threaded upload")
        try:
            uploaded_videos = youtube_bulk_upload.process()
            message = f"Upload complete! Videos uploaded: {len(uploaded_videos)}"
            self.gui_root.after(0, lambda: messagebox.showinfo("Success", message))
        except Exception as e:
            error_message = f"An error occurred during upload: {str(e)}"
            self.logger.error(error_message)
            # Ensure the error message is shown in the GUI as well
            self.gui_root.after(0, lambda msg=error_message: messagebox.showerror("Error", msg))

    def select_client_secrets_file(self):
        self.logger.debug("Selecting client secrets file")
        filename = filedialog.askopenfilename(title="Select Client Secrets File", filetypes=[("JSON files", "*.json")])
        if filename:
            self.yt_client_secrets_file_var.set(filename)

    def select_source_directory(self):
        self.logger.debug("Selecting source directory")
        directory = filedialog.askdirectory(title="Select Source Directory")
        if directory:
            self.source_directory_var.set(directory)

    def select_yt_desc_template_file(self):
        self.logger.debug("Selecting YouTube description template file")
        filename = filedialog.askopenfilename(title="Select YouTube Description Template File", filetypes=[("Text files", "*.txt")])
        if filename:
            self.yt_desc_template_file_var.set(filename)

    def clear_log(self):
        self.logger.debug("Clearing log output")
        self.log_output.config(state=tk.NORMAL)  # Enable text widget for editing
        self.log_output.delete("1.0", tk.END)
        self.log_output.config(state=tk.DISABLED)  # Disable text widget after clearing


class ReusableWidgetFrame(tk.LabelFrame):
    def __init__(self, parent, logger, title, **kwargs):
        self.logger = logger
        self.logger.debug(f"Initializing ReusableWidgetFrame with title: {title}")
        kwargs.setdefault("padx", 10)  # Add default padding on the x-axis
        kwargs.setdefault("pady", 10)  # Add default padding on the y-axis
        super().__init__(parent, text=title, **kwargs)
        self.find_var = tk.StringVar()
        self.replace_var = tk.StringVar()
        self.row = 0  # Keep track of the next row index to add widgets

    def new_row(self):
        self.logger.debug("Adding a new row in ReusableWidgetFrame")
        self.row += 1

    def add_widgets(self, widgets):
        self.logger.debug(f"Adding widgets: {widgets}")
        for widget in widgets:
            widget.grid(row=self.row, column=0, columnspan=2, sticky="ew", padx=5, pady=2)
            self.row += 1

    def add_find_replace_widgets(self, label_text, summary_tooltip_text):
        self.logger.debug(f"Adding find/replace widgets with label: {label_text}")

        label = tk.Label(self, text=label_text)
        label.grid(row=self.row, column=0, sticky="w")
        Tooltip(label, summary_tooltip_text)

        # Listbox with a scrollbar for replacements
        self.row += 1
        self.replacements_listbox = tk.Listbox(self, height=4, width=50)
        scrollbar = tk.Scrollbar(self, orient="vertical", command=self.replacements_listbox.yview)
        self.replacements_listbox.config(yscrollcommand=scrollbar.set)
        self.replacements_listbox.grid(row=self.row, column=0, columnspan=2, sticky="nsew", padx=(5, 0), pady=5)
        scrollbar.grid(row=self.row, column=2, sticky="ns", pady=5)
        Tooltip(self.replacements_listbox, "Currently active find/replace pairs.")

        # Entry fields for adding new find/replace pairs
        self.row += 1
        find_entry = tk.Entry(self, textvariable=self.find_var, width=20)
        find_entry.grid(row=self.row, column=0, sticky="ew", padx=(5, 0), pady=(5, 0))
        replace_entry = tk.Entry(self, textvariable=self.replace_var, width=20)
        replace_entry.grid(row=self.row, column=1, sticky="ew", pady=(5, 0))
        Tooltip(find_entry, "Enter text to find. Supports regex syntax for advanced patterns, e.g. [0-9]+ for a sequence of digits.")
        Tooltip(
            replace_entry,
            "Enter replacement text. Use regex syntax for advanced patterns, including references to capture strings in the matched text. Leave blank to delete matched text.",
        )

        # Buttons for adding and removing replacements
        self.row += 1
        add_button = tk.Button(self, text="Add Replacement", command=self.add_replacement)
        add_button.grid(row=self.row, column=0, sticky="ew", padx=(5, 0), pady=5)
        remove_button = tk.Button(self, text="Remove Selected", command=self.remove_replacement)
        remove_button.grid(row=self.row, column=1, sticky="ew", pady=5)
        Tooltip(add_button, "Add a new find/replace pair.")
        Tooltip(remove_button, "Remove the selected find/replace pair.")

    def add_replacement(self):
        self.logger.debug("Adding a replacement")
        find_text = self.find_var.get()
        replace_text = self.replace_var.get()
        if find_text:
            self.replacements_listbox.insert(tk.END, f"{find_text} -> {replace_text}")
            self.find_var.set("")
            self.replace_var.set("")

    def remove_replacement(self):
        self.logger.debug("Removing selected replacements")
        selected_indices = self.replacements_listbox.curselection()
        for i in reversed(selected_indices):
            self.replacements_listbox.delete(i)

    def get_replacements(self):
        replacements = []
        listbox_items = self.replacements_listbox.get(0, tk.END)
        for item in listbox_items:
            find, replace = item.split(" -> ")
            replacements.append((find, replace))
        return replacements


class Tooltip:
    """
    Create a tooltip for a given widget.
    """

    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)

    def enter(self, event=None):
        # Get the widget's location on the screen
        x = self.widget.winfo_rootx()
        y = self.widget.winfo_rooty()
        # Adjust the y-coordinate to show the tooltip above the widget or at its top
        y += 28  # Adjust this value as needed to position the tooltip correctly

        # x, y, cx, cy = self.widget.bbox("insert")  # Get widget size
        # x += self.widget.winfo_rootx()
        # y += self.widget.winfo_rooty() + 28

        # Create a toplevel window with required properties
        self.tooltip_window = tk.Toplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            self.tooltip_window,
            text=self.text,
            justify="left",
            padx=5,
            pady=5,
            borderwidth=1,
            relief="solid",
            highlightbackground="#00FF00",
            highlightcolor="#00FF00",
            highlightthickness=1,
            wraplength=350,
        )
        label.pack(ipadx=1)

    def leave(self, event=None):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None


class TextHandler(logging.Handler):
    def __init__(self, logger, text_widget):
        self.logger = logger
        self.logger.debug("Initializing TextHandler")
        super().__init__()
        self.text_widget = text_widget

    def emit(self, record):
        msg = self.format(record)
        self.text_widget.config(state=tk.NORMAL)  # Enable text widget for editing
        self.text_widget.insert(tk.END, msg + "\n")
        self.text_widget.see(tk.END)
        self.text_widget.config(state=tk.DISABLED)  # Disable text widget after updating


class DualLogger:
    """
    A class that can be used to log to both a file and the console at the same time.
    This is used to log to the GUI and to a file at the same time.
    Multiple instances can be used pointing to the same file, and each instance will not overwrite one another.
    """

    _lock = threading.Lock()  # Class-level lock shared by all instances

    def __init__(self, file_path, stream):
        try:
            self.file = open(file_path, "a")  # Open in append mode
        except Exception as e:
            print(f"Failed to open log file {file_path}: {e}")
            self.file = None
        self.stream = stream

    def write(self, message):
        with self._lock:  # Ensure only one thread can enter this block at a time
            if self.file is not None:
                self.file.write(message)
            if self.stream is not None:
                self.stream.write(message)
            self.flush()  # Ensure the message is written immediately

    def flush(self):
        if self.file is not None:
            self.file.flush()
        if self.stream is not None:
            self.stream.flush()


def main():
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        bundle_dir = Path(sys._MEIPASS)
        # If we're running from a PyInstaller bundle, log to user's home dir
        user_home_dir = os.path.expanduser("~")
        log_filepath = os.path.join(user_home_dir, "youtube_bulk_upload.log")
        running_in_pyinstaller = True
    else:
        bundle_dir = Path(__file__).parent.parent
        # If this GUI was launched from the command line, log to the current directory
        log_filepath = os.path.join(bundle_dir, "youtube_bulk_upload.log")
        running_in_pyinstaller = False

    sys.stdout = DualLogger(log_filepath, sys.stdout)
    sys.stderr = DualLogger(log_filepath, sys.stderr)

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    log_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(module)s - %(message)s")

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_formatter)
    logger.addHandler(console_handler)

    logger.info(f"YouTubeBulkUploaderGUI launched, PyInstaller: {running_in_pyinstaller}, Logging to stdout and file: {log_filepath}")

    logger.info("Creating Tkinter GUI root object")
    gui_root = tk.Tk()

    try:
        app = YouTubeBulkUploaderGUI(gui_root, logger, bundle_dir, running_in_pyinstaller)

        logger.debug("Starting main GUI loop")

        logger.info(f"If you have encounter any issues with YouTube Bulk Upload, please send Andrew the logs from the file path below!")
        logger.info(f"Log file path: {log_filepath}")

        gui_root.mainloop()
    except Exception as e:
        logger.error(str(e))

        # Pass the error_message variable to the lambda function
        gui_root.after(0, lambda msg=str(e): messagebox.showerror("Error", msg))


if __name__ == "__main__":
    main()
