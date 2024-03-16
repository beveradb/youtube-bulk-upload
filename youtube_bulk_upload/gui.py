import tkinter as tk
from tkinter import filedialog, messagebox
from youtube_bulk_upload import YouTubeBulkUpload


class YouTubeBulkUploaderGUI:
    def __init__(self, root):
        self.root = root
        self.setup_ui()

    def setup_ui(self):
        self.root.title("YouTube Bulk Upload")

        # Define variables for inputs
        self.log_level_var = tk.StringVar(value="info")
        self.dry_run_var = tk.BooleanVar()
        self.noninteractive_var = tk.BooleanVar()

        # Create input fields
        tk.Label(self.root, text="Log Level:").pack()
        tk.Entry(self.root, textvariable=self.log_level_var).pack()

        tk.Checkbutton(self.root, text="Dry Run", variable=self.dry_run_var).pack()
        tk.Checkbutton(self.root, text="Non-interactive", variable=self.noninteractive_var).pack()

        tk.Label(self.root, text="Input File Extensions (space-separated):").pack()
        self.input_file_extensions_entry = tk.Entry(self.root)
        self.input_file_extensions_entry.pack()

        tk.Label(self.root, text="Upload Batch Limit:").pack()
        self.upload_batch_limit_entry = tk.Entry(self.root)
        self.upload_batch_limit_entry.pack()

        # Run button
        tk.Button(self.root, text="Run", command=self.run_upload).pack()

    def run_upload(self):
        # Collect values from GUI
        log_level = self.log_level_var.get()
        dry_run = self.dry_run_var.get()
        noninteractive = self.noninteractive_var.get()
        input_file_extensions = self.input_file_extensions_entry.get().split()
        upload_batch_limit = int(self.upload_batch_limit_entry.get())

        # Initialize YouTubeBulkUpload with collected parameters
        youtube_bulk_upload = YouTubeBulkUpload(
            log_level=log_level,
            dry_run=dry_run,
            interactive_prompt=not noninteractive,
            input_file_extensions=input_file_extensions,
            upload_batch_limit=upload_batch_limit,
            # Add other parameters here
        )

        try:
            uploaded_videos = youtube_bulk_upload.process()
            messagebox.showinfo("Success", f"Upload complete! Videos uploaded: {len(uploaded_videos)}")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")


def main():
    root = tk.Tk()
    app = YouTubeBulkUploaderGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
