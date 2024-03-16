import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from youtube_bulk_upload import YouTubeBulkUpload
import logging
import threading
import pkg_resources  # Make sure to import pkg_resources


class YouTubeBulkUploaderGUI:
    def __init__(self, root):
        self.root = root
        self.setup_ui()

    def setup_ui(self):
        # Fetch the package version
        package_version = pkg_resources.get_distribution("youtube-bulk-upload").version
        self.root.title(f"YouTube Bulk Upload - v{package_version}")
        self.root.minsize(800, 600)

        # General Options Frame
        self.general_frame = tk.LabelFrame(self.root, text="General Options")
        self.general_frame.grid(row=0, column=0, padx=10, pady=5, sticky="nsew")

        # YouTube General Options Frame
        self.youtube_general_frame = tk.LabelFrame(self.root, text="YouTube General Options")
        self.youtube_general_frame.grid(row=0, column=1, padx=10, pady=5, sticky="nsew")

        # YouTube Title Frame
        self.youtube_title_frame = tk.LabelFrame(self.root, text="YouTube Title")
        self.youtube_title_frame.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")

        # YouTube Description Frame
        self.youtube_desc_frame = tk.LabelFrame(self.root, text="YouTube Description")
        self.youtube_desc_frame.grid(row=1, column=1, padx=10, pady=5, sticky="nsew")

        # Thumbnail Options Frame
        self.thumbnail_frame = tk.LabelFrame(self.root, text="Thumbnail Options")
        self.thumbnail_frame.grid(row=2, column=0, padx=10, pady=5, sticky="nsew")

        # Configure the grid layout to allow frames to resize properly
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)

        # Define variables for inputs
        self.log_level_var = tk.StringVar(value="info")
        self.dry_run_var = tk.BooleanVar()
        self.noninteractive_var = tk.BooleanVar()
        self.yt_client_secrets_file_var = tk.StringVar(value="client_secret.json")
        self.yt_category_id_var = tk.StringVar(value="10")
        self.yt_keywords_var = tk.StringVar(value="music")
        self.yt_desc_template_file_var = tk.StringVar(value="description_template.txt")
        self.yt_title_prefix_var = tk.StringVar()
        self.yt_title_suffix_var = tk.StringVar()
        self.thumb_file_prefix_var = tk.StringVar()
        self.thumb_file_suffix_var = tk.StringVar()
        self.thumb_file_extensions_var = tk.StringVar(value=".png .jpg .jpeg")

        # Create input fields in General Options frame
        tk.Label(self.general_frame, text="Log Level:").grid(row=0, column=0, sticky="w")
        tk.Entry(self.general_frame, textvariable=self.log_level_var).grid(row=0, column=1, sticky="ew")

        tk.Checkbutton(self.general_frame, text="Dry Run", variable=self.dry_run_var).grid(row=1, column=0, sticky="w")
        tk.Checkbutton(self.general_frame, text="Non-interactive", variable=self.noninteractive_var).grid(row=1, column=1, sticky="ew")

        tk.Label(self.general_frame, text="Input File Extensions (space-separated):").grid(row=2, column=0, sticky="w")
        self.input_file_extensions_entry = tk.Entry(self.general_frame)
        self.input_file_extensions_entry.grid(row=2, column=1, sticky="ew")

        tk.Label(self.general_frame, text="Upload Batch Limit:").grid(row=3, column=0, sticky="w")
        self.upload_batch_limit_entry = tk.Entry(self.general_frame)
        self.upload_batch_limit_entry.grid(row=3, column=1, sticky="ew")

        # Additional YouTube Options in YouTube General Options frame
        tk.Label(self.youtube_general_frame, text="YouTube Client Secrets File:").grid(row=0, column=0, sticky="w")
        tk.Entry(self.youtube_general_frame, textvariable=self.yt_client_secrets_file_var).grid(row=0, column=1, sticky="ew")
        self.yt_client_secrets_file_button = tk.Button(
            self.youtube_general_frame, text="Browse...", command=self.select_client_secrets_file
        )
        self.yt_client_secrets_file_button.grid(row=0, column=2, padx=5, pady=5, sticky="ew")

        tk.Label(self.youtube_general_frame, text="YouTube Category ID:").grid(row=1, column=0, sticky="w")
        tk.Entry(self.youtube_general_frame, textvariable=self.yt_category_id_var).grid(row=1, column=1, sticky="ew")

        tk.Label(self.youtube_general_frame, text="YouTube Keywords (space-separated):").grid(row=2, column=0, sticky="w")
        tk.Entry(self.youtube_general_frame, textvariable=self.yt_keywords_var).grid(row=2, column=1, sticky="ew")

        # YouTube Title Options in YouTube Title frame
        tk.Label(self.youtube_title_frame, text="YouTube Title Prefix:").grid(row=0, column=0, sticky="w")
        tk.Entry(self.youtube_title_frame, textvariable=self.yt_title_prefix_var).grid(row=0, column=1, sticky="ew")

        tk.Label(self.youtube_title_frame, text="YouTube Title Suffix:").grid(row=1, column=0, sticky="w")
        tk.Entry(self.youtube_title_frame, textvariable=self.yt_title_suffix_var).grid(row=1, column=1, sticky="ew")

        # YouTube Description Options in YouTube Description frame
        tk.Label(self.youtube_desc_frame, text="YouTube Description Template File:").grid(row=0, column=0, sticky="w")
        tk.Entry(self.youtube_desc_frame, textvariable=self.yt_desc_template_file_var).grid(row=0, column=1, sticky="ew")

        # Thumbnail Options in Thumbnail Options frame
        tk.Label(self.thumbnail_frame, text="Thumbnail File Prefix:").grid(row=0, column=0, sticky="w")
        tk.Entry(self.thumbnail_frame, textvariable=self.thumb_file_prefix_var).grid(row=0, column=1, sticky="ew")

        tk.Label(self.thumbnail_frame, text="Thumbnail File Suffix:").grid(row=1, column=0, sticky="w")
        tk.Entry(self.thumbnail_frame, textvariable=self.thumb_file_suffix_var).grid(row=1, column=1, sticky="ew")

        tk.Label(self.thumbnail_frame, text="Thumbnail File Extensions (space-separated):").grid(row=2, column=0, sticky="w")
        tk.Entry(self.thumbnail_frame, textvariable=self.thumb_file_extensions_var).grid(row=2, column=1, sticky="ew")

        # Adjust padding and spacing
        for frame in [
            self.general_frame,
            self.youtube_general_frame,
            self.youtube_title_frame,
            self.youtube_desc_frame,
            self.thumbnail_frame,
        ]:
            for child in frame.winfo_children():
                child.grid_configure(padx=5, pady=5)  # Add consistent padding

        # Run button
        self.run_button = tk.Button(self.root, text="Run", command=self.run_upload)
        self.run_button.grid(row=3, column=0, padx=10, pady=5, sticky="ew")

        # Clear log button
        self.clear_log_button = tk.Button(self.root, text="Clear Log", command=self.clear_log)
        self.clear_log_button.grid(row=3, column=1, padx=5, pady=5, sticky="ew")

        # Log output at the bottom spanning both columns
        tk.Label(self.root, text="Log Output:").grid(row=4, column=0, columnspan=2, sticky="w")
        self.log_output = scrolledtext.ScrolledText(self.root, height=10)
        self.log_output.grid(row=5, column=0, columnspan=2, padx=10, pady=5, sticky="nsew")
        self.log_output.config(state=tk.DISABLED)  # Make log output read-only

        # Setup logging to text widget
        self.setup_logging()

    def setup_logging(self):
        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)
        log_handler = TextHandler(self.log_output)
        log_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        logger.addHandler(log_handler)

    def run_upload(self):
        # Collect values from GUI
        log_level = self.log_level_var.get()
        dry_run = self.dry_run_var.get()
        noninteractive = self.noninteractive_var.get()
        input_file_extensions = self.input_file_extensions_entry.get().split()
        upload_batch_limit = int(self.upload_batch_limit_entry.get())
        yt_client_secrets_file = self.yt_client_secrets_file_var.get()
        yt_category_id = self.yt_category_id_var.get()
        yt_keywords = self.yt_keywords_var.get().split()
        yt_desc_template_file = self.yt_desc_template_file_var.get()
        yt_title_prefix = self.yt_title_prefix_var.get()
        yt_title_suffix = self.yt_title_suffix_var.get()
        thumb_file_prefix = self.thumb_file_prefix_var.get()
        thumb_file_suffix = self.thumb_file_suffix_var.get()
        thumb_file_extensions = self.thumb_file_extensions_var.get().split()

        # Initialize YouTubeBulkUpload with collected parameters
        youtube_bulk_upload = YouTubeBulkUpload(
            log_level=log_level,
            dry_run=dry_run,
            interactive_prompt=not noninteractive,
            input_file_extensions=input_file_extensions,
            upload_batch_limit=upload_batch_limit,
            youtube_client_secrets_file=yt_client_secrets_file,
            youtube_category_id=yt_category_id,
            youtube_keywords=yt_keywords,
            youtube_description_template_file=yt_desc_template_file,
            youtube_title_prefix=yt_title_prefix,
            youtube_title_suffix=yt_title_suffix,
            thumbnail_filename_prefix=thumb_file_prefix,
            thumbnail_filename_suffix=thumb_file_suffix,
            thumbnail_filename_extensions=thumb_file_extensions,
        )

        # Run the upload process in a separate thread to prevent GUI freezing
        upload_thread = threading.Thread(target=self.threaded_upload, args=(youtube_bulk_upload,))
        upload_thread.start()

    def select_client_secrets_file(self):
        filename = filedialog.askopenfilename(title="Select Client Secrets File", filetypes=[("JSON files", "*.json")])
        if filename:
            self.yt_client_secrets_file_var.set(filename)

    def clear_log(self):
        self.log_output.config(state=tk.NORMAL)  # Enable text widget for editing
        self.log_output.delete("1.0", tk.END)
        self.log_output.config(state=tk.DISABLED)  # Disable text widget after clearing

    def threaded_upload(self, youtube_bulk_upload):
        try:
            uploaded_videos = youtube_bulk_upload.process()
            messagebox.showinfo("Success", f"Upload complete! Videos uploaded: {len(uploaded_videos)}")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")
        finally:
            self.log_output.config(state=tk.NORMAL)  # Enable text widget for editing
            self.log_output.insert(tk.END, f"Upload process completed with {len(uploaded_videos)} videos uploaded.\n")
            self.log_output.config(state=tk.DISABLED)  # Disable text widget after updating


class TextHandler(logging.Handler):
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget

    def emit(self, record):
        msg = self.format(record)
        self.text_widget.config(state=tk.NORMAL)  # Enable text widget for editing
        self.text_widget.insert(tk.END, msg + "\n")
        self.text_widget.see(tk.END)
        self.text_widget.config(state=tk.DISABLED)  # Disable text widget after updating


def main():
    root = tk.Tk()
    app = YouTubeBulkUploaderGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
