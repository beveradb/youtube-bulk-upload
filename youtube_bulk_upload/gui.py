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

    def add_find_replace_widgets(self, label_text):
        self.logger.debug(f"Adding find/replace widgets with label: {label_text}")
        tk.Label(self, text=label_text).grid(row=self.row, column=0, sticky="w")

        # Listbox with a scrollbar for replacements
        self.row += 1
        self.replacements_listbox = tk.Listbox(self, height=4, width=50)
        scrollbar = tk.Scrollbar(self, orient="vertical", command=self.replacements_listbox.yview)
        self.replacements_listbox.config(yscrollcommand=scrollbar.set)
        self.replacements_listbox.grid(row=self.row, column=0, columnspan=2, sticky="nsew", padx=(5, 0), pady=5)
        scrollbar.grid(row=self.row, column=2, sticky="ns", pady=5)

        # Entry fields for adding new find/replace pairs
        self.row += 1
        tk.Entry(self, textvariable=self.find_var, width=20).grid(row=self.row, column=0, sticky="ew", padx=(5, 0), pady=(5, 0))
        tk.Entry(self, textvariable=self.replace_var, width=20).grid(row=self.row, column=1, sticky="ew", pady=(5, 0))

        # Buttons for adding and removing replacements
        self.row += 1
        add_button = tk.Button(self, text="Add Replacement", command=self.add_replacement)
        add_button.grid(row=self.row, column=0, sticky="ew", padx=(5, 0), pady=5)
        remove_button = tk.Button(self, text="Remove Selected", command=self.remove_replacement)
        remove_button.grid(row=self.row, column=1, sticky="ew", pady=5)

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

        self.dry_run_var = tk.BooleanVar()
        self.noninteractive_var = tk.BooleanVar()
        self.source_directory_var = tk.StringVar(value=os.path.expanduser("~"))
        self.yt_client_secrets_file_var = tk.StringVar(value="client_secret.json")
        self.yt_category_id_var = tk.StringVar(value="10")
        self.yt_keywords_var = tk.StringVar(value="music")
        self.yt_desc_template_file_var = tk.StringVar()
        self.yt_title_prefix_var = tk.StringVar()
        self.yt_title_suffix_var = tk.StringVar()
        self.thumb_file_prefix_var = tk.StringVar()
        self.thumb_file_suffix_var = tk.StringVar()
        self.thumb_file_extensions_var = tk.StringVar(value=".png .jpg .jpeg")

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

        user_home_dir = os.path.expanduser("~")
        self.gui_config_filepath = os.path.join(user_home_dir, "youtube_bulk_upload_config.json")
        self.load_gui_config_options()  # Load configurations on initialization

        self.user_input_event = threading.Event()
        self.user_input_result = None

        self.logger.info("YouTubeBulkUploaderGUI Initialized")

    def load_gui_config_options(self):
        self.logger.info(f"Loading GUI configuration values from file: {self.gui_config_filepath}")

        try:
            with open(self.gui_config_filepath, "r") as f:
                config = json.load(f)
                # Set the variables' values from the config file
                self.log_level_var.set(config.get("log_level", "info"))
                self.dry_run_var.set(config.get("dry_run", False))
                self.noninteractive_var.set(config.get("noninteractive", False))
                self.source_directory_var.set(config.get("source_directory", os.path.expanduser("~")))
                self.yt_client_secrets_file_var.set(config.get("yt_client_secrets_file", "client_secret.json"))
                self.yt_category_id_var.set(config.get("yt_category_id", "10"))
                self.yt_keywords_var.set(config.get("yt_keywords", "music"))
                self.yt_desc_template_file_var.set(config.get("yt_desc_template_file", ""))
                self.yt_title_prefix_var.set(config.get("yt_title_prefix", ""))
                self.yt_title_suffix_var.set(config.get("yt_title_suffix", ""))
                self.thumb_file_prefix_var.set(config.get("thumb_file_prefix", ""))
                self.thumb_file_suffix_var.set(config.get("thumb_file_suffix", ""))
                self.thumb_file_extensions_var.set(config.get("thumb_file_extensions", ".png .jpg .jpeg"))

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
        }
        with open(self.gui_config_filepath, "w") as f:
            json.dump(config, f, indent=4)

    def on_log_level_change(self, *args):
        self.logger.debug(f"Log level changed to: {self.log_level_var.get()}")

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

        # Run and Clear Log buttons
        self.run_button = tk.Button(self.gui_root, text="Run", command=self.run_upload)
        self.run_button.grid(row=self.row, column=0, padx=10, pady=5, sticky="ew")
        self.clear_log_button = tk.Button(self.gui_root, text="Clear Log", command=self.clear_log)
        self.clear_log_button.grid(row=self.row, column=1, padx=10, pady=5, sticky="ew")

        self.row += 1

        # Log output at the bottom spanning both columns
        tk.Label(self.gui_root, text="Log Output:").grid(row=self.row, column=0, columnspan=2, sticky="w")
        self.log_output = scrolledtext.ScrolledText(self.gui_root, height=10)
        self.log_output.grid(row=self.row, column=0, columnspan=2, padx=10, pady=5, sticky="nsew")
        self.log_output.config(state=tk.DISABLED)  # Make log output read-only

    def add_general_options_widgets(self):
        frame = self.general_frame

        tk.Label(self.general_frame, text="Log Level:").grid(row=frame.row, column=0, sticky="w")
        tk.OptionMenu(self.general_frame, self.log_level_var, "info", "warning", "error", "debug").grid(
            row=frame.row, column=1, sticky="ew"
        )

        frame.new_row()
        tk.Checkbutton(self.general_frame, text="Dry Run", variable=self.dry_run_var).grid(row=frame.row, column=0, sticky="w")
        tk.Checkbutton(self.general_frame, text="Non-interactive", variable=self.noninteractive_var).grid(
            row=frame.row, column=1, sticky="w"
        )

        frame.new_row()
        tk.Label(self.general_frame, text="Source Directory:").grid(row=frame.row, column=0, sticky="w")
        tk.Entry(self.general_frame, textvariable=self.source_directory_var).grid(row=frame.row, column=1, sticky="ew")
        tk.Button(self.general_frame, text="Browse...", command=self.select_source_directory).grid(row=frame.row, column=2, sticky="ew")

        # YouTube Client Secrets File
        frame.new_row()
        tk.Label(self.general_frame, text="YouTube Client Secrets File:").grid(row=frame.row, column=0, sticky="w")
        tk.Entry(self.general_frame, textvariable=self.yt_client_secrets_file_var).grid(row=frame.row, column=1, sticky="ew")
        tk.Button(self.general_frame, text="Browse...", command=self.select_client_secrets_file).grid(row=frame.row, column=2, sticky="ew")

        # Input File Extensions
        frame.new_row()
        tk.Label(self.general_frame, text="Input File Extensions:").grid(row=frame.row, column=0, sticky="w")
        self.input_file_extensions_var = tk.StringVar(value=".mp4 .mov")  # Default value
        tk.Entry(self.general_frame, textvariable=self.input_file_extensions_var).grid(row=frame.row, column=1, sticky="ew")

        # Upload Batch Limit
        frame.new_row()
        tk.Label(self.general_frame, text="Upload Batch Limit:").grid(row=frame.row, column=0, sticky="w")
        self.upload_batch_limit_var = tk.IntVar(value=100)  # Default value
        tk.Entry(self.general_frame, textvariable=self.upload_batch_limit_var).grid(row=frame.row, column=1, sticky="ew")

        # YouTube Category ID
        frame.new_row()
        tk.Label(self.general_frame, text="YouTube Category ID:").grid(row=frame.row, column=0, sticky="w")
        tk.Entry(self.general_frame, textvariable=self.yt_category_id_var).grid(row=frame.row, column=1, sticky="ew")

        # YouTube Keywords
        frame.new_row()
        tk.Label(self.general_frame, text="YouTube Keywords:").grid(row=frame.row, column=0, sticky="w")
        tk.Entry(self.general_frame, textvariable=self.yt_keywords_var).grid(row=frame.row, column=1, sticky="ew")

    def add_youtube_title_widgets(self):
        frame = self.youtube_title_frame
        tk.Label(self.youtube_title_frame, text="Prefix:").grid(row=frame.row, column=0, sticky="w")
        tk.Entry(self.youtube_title_frame, textvariable=self.yt_title_prefix_var).grid(row=frame.row, column=1, sticky="ew")

        frame.new_row()
        tk.Label(self.youtube_title_frame, text="Suffix:").grid(row=frame.row, column=0, sticky="w")
        tk.Entry(self.youtube_title_frame, textvariable=self.yt_title_suffix_var).grid(row=frame.row, column=1, sticky="ew")

        frame.new_row()
        self.youtube_title_frame.add_find_replace_widgets("Find / Replace Patterns:")

    def add_youtube_description_widgets(self):
        frame = self.youtube_desc_frame
        tk.Label(self.youtube_desc_frame, text="Template File:").grid(row=frame.row, column=0, sticky="w")
        tk.Entry(self.youtube_desc_frame, textvariable=self.yt_desc_template_file_var, state="readonly").grid(
            row=frame.row, column=1, sticky="ew"
        )
        tk.Button(self.youtube_desc_frame, text="Browse...", command=self.select_yt_desc_template_file).grid(
            row=frame.row, column=2, sticky="ew"
        )

        frame.new_row()
        self.youtube_desc_frame.add_find_replace_widgets("Find / Replace Patterns:")

    def add_thumbnail_options_widgets(self):
        frame = self.thumbnail_frame
        tk.Label(self.thumbnail_frame, text="Filename Prefix:").grid(row=frame.row, column=0, sticky="w")
        tk.Entry(self.thumbnail_frame, textvariable=self.thumb_file_prefix_var).grid(row=frame.row, column=1, sticky="ew")

        frame.new_row()
        tk.Label(self.thumbnail_frame, text="Filename Suffix:").grid(row=frame.row, column=0, sticky="w")
        tk.Entry(self.thumbnail_frame, textvariable=self.thumb_file_suffix_var).grid(row=frame.row, column=1, sticky="ew")

        frame.new_row()
        tk.Label(self.thumbnail_frame, text="File Extensions:").grid(row=frame.row, column=0, sticky="w")
        tk.Entry(self.thumbnail_frame, textvariable=self.thumb_file_extensions_var).grid(row=frame.row, column=1, sticky="ew")

        frame.new_row()
        self.thumbnail_frame.add_find_replace_widgets("Find / Replace Patterns:")

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

    def run_upload(self):
        self.logger.info("Initializing YouTubeBulkUpload class with parameters from GUI")

        dry_run = self.dry_run_var.get()
        noninteractive = self.noninteractive_var.get()
        source_directory = self.source_directory_var.get()
        yt_client_secrets_file = self.yt_client_secrets_file_var.get()
        yt_category_id = self.yt_category_id_var.get()
        yt_keywords = self.yt_keywords_var.get().split()
        yt_desc_template_file = self.yt_desc_template_file_var.get()
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
        self.file = open(file_path, "a")  # Open in append mode
        self.stream = stream

    def write(self, message):
        with self._lock:  # Ensure only one thread can enter this block at a time
            self.file.write(message)
            self.stream.write(message)
            self.flush()  # Ensure the message is written immediately

    def flush(self):
        self.file.flush()
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
