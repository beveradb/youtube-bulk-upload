import os
import json
import tempfile
import logging
import re
import pickle
from thefuzz import fuzz
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.http import MediaFileUpload

YOUTUBE_URL_PREFIX = "https://www.youtube.com/watch?v="


class YouTubeBulkUpload:
    def __init__(
        self,
        logger=None,
        log_level=logging.DEBUG,
        log_formatter=None,
        dry_run=False,
        interactive_prompt=True,
        stop_event=None,
        gui=None,
        source_directory=os.getcwd(),
        input_file_extensions=[".mp4", ".mov"],
        upload_batch_limit=100,
        youtube_client_secrets_file=None,
        youtube_category_id="10",  # Category ID for Music
        youtube_keywords=["music"],
        youtube_description_template_file=None,
        youtube_description_replacements=None,
        youtube_title_prefix=None,
        youtube_title_suffix=None,
        youtube_title_replacements=None,
        thumbnail_filename_prefix=None,
        thumbnail_filename_suffix=None,
        thumbnail_filename_replacements=None,
        thumbnail_filename_extensions=[".png", ".jpg", ".jpeg"],
    ):
        self.logger = logger

        if self.logger is None:
            self.logger = logging.getLogger(__name__)
            self.logger.setLevel(log_level)
            self.log_level = log_level
            self.log_formatter = log_formatter

            self.log_handler = logging.StreamHandler()

            if self.log_formatter is None:
                self.log_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(module)s - %(message)s")

            self.log_handler.setFormatter(self.log_formatter)
            self.logger.addHandler(self.log_handler)

        self.logger.info(
            f"YouTubeBulkUpload instantiating, dry_run: {dry_run}, interactive_prompt: {interactive_prompt}, source_directory: {source_directory}, input_file_extensions: {input_file_extensions}"
        )
        self.logger.info(
            f"youtube_client_secrets_file: {youtube_client_secrets_file}, youtube_description_template_file: {youtube_description_template_file}"
        )
        self.logger.info(f"youtube_title_replacements: {youtube_title_replacements}, youtube_title_prefix: {youtube_title_prefix}")
        self.logger.info(f"youtube_title_suffix: {youtube_title_suffix}")
        self.logger.info(f"thumbnail_filename_prefix: {thumbnail_filename_prefix}, thumbnail_filename_suffix: {thumbnail_filename_suffix}")
        self.logger.info(
            f"thumbnail_filename_replacements: {thumbnail_filename_replacements}, thumbnail_filename_extensions: {thumbnail_filename_extensions}"
        )

        self.gui = gui
        self.stop_event = stop_event
        self.dry_run = dry_run

        self.source_directory = source_directory
        self.input_file_extensions = input_file_extensions

        self.youtube_client_secrets_file = youtube_client_secrets_file

        self.youtube_category_id = youtube_category_id
        self.youtube_keywords = youtube_keywords

        self.youtube_description_template_file = youtube_description_template_file
        self.youtube_description_replacements = youtube_description_replacements

        self.youtube_title_prefix = youtube_title_prefix
        self.youtube_title_suffix = youtube_title_suffix
        self.youtube_title_replacements = youtube_title_replacements

        self.thumbnail_filename_prefix = thumbnail_filename_prefix
        self.thumbnail_filename_suffix = thumbnail_filename_suffix
        self.thumbnail_filename_replacements = thumbnail_filename_replacements
        self.thumbnail_filename_extensions = thumbnail_filename_extensions

        self.interactive_prompt = interactive_prompt
        self.upload_batch_limit = upload_batch_limit

    def find_input_files(self):
        self.logger.info(f"Finding input video files to upload...")

        video_files = [
            os.path.join(self.source_directory, f)
            for f in os.listdir(self.source_directory)
            if f.endswith(tuple(self.input_file_extensions))
        ]
        if not video_files:
            self.logger.error(f"No video files found in current directory to upload.")
            raise Exception(f"No video files found in current directory to upload.")

        self.logger.info(f"Found {len(video_files)} video files to upload.")

        return video_files

    def prompt_user_confirmation_or_raise_exception(self, prompt_message, exit_message, allow_empty=False):
        if not self.prompt_user_bool(prompt_message, allow_empty=allow_empty):
            self.logger.error(exit_message)
            raise Exception(exit_message)

    def prompt_user_bool(self, prompt_message, allow_empty=False):
        if self.gui is not None:
            # Trigger the GUI prompt (this will return immediately)
            self.gui.prompt_user_bool(prompt_message=prompt_message, allow_empty=allow_empty)

            # Wait for the user to provide input or close the dialog
            self.gui.user_input_event.wait()

            # Once the event is set, retrieve the input
            user_input = self.gui.user_input_result
            return user_input
        else:
            options_string = "[y]/n" if allow_empty else "y/[n]"
            accept_responses = ["y", "yes"]
            if allow_empty:
                accept_responses.append("")

            print()
            response = input(f"{prompt_message} {options_string} ")
            return response.strip().lower() in accept_responses

    def prompt_user_text(self, prompt_message, default_response=""):
        if self.gui is not None:
            # Trigger the GUI prompt (this will return immediately)
            self.gui.prompt_user_text(prompt_message, default_response)

            # Wait for the user to provide input or close the dialog
            self.gui.user_input_event.wait()

            # Once the event is set, retrieve the input
            user_input = self.gui.user_input_result
            return user_input

        else:
            return input(prompt_message)

    def validate_input_parameters(self):
        self.logger.info(f"Validating input parameters for enabled features...")

        current_directory = os.getcwd()
        self.logger.info(f"Current directory to process: {current_directory}")

        # Enable youtube upload if client secrets file is provided and is valid JSON
        if self.youtube_client_secrets_file is None or not os.path.isfile(self.youtube_client_secrets_file):
            raise Exception(f"YouTube client secrets file does not exist: {self.youtube_client_secrets_file}")

        if self.youtube_description_template_file is None:
            self.logger.warn("No YouTube description template file provided. Description will be empty unless entered interactively.")
        else:
            if not os.path.isfile(self.youtube_description_template_file):
                raise Exception(f"YouTube description file does not exist: {self.youtube_description_template_file}")

            self.logger.info(f"YouTube description template file exists: {self.youtube_description_template_file}")

        # Test parsing the file as JSON to check it's valid
        try:
            with open(self.youtube_client_secrets_file, "r", encoding="utf-8") as f:
                json.load(f)
                self.logger.info(f"YouTube client secrets file is valid JSON: {self.youtube_client_secrets_file}")
        except json.JSONDecodeError as e:
            raise Exception(f"YouTube client secrets file is not valid JSON: {self.youtube_client_secrets_file}") from e

        self.logger.debug(f"YouTube upload checks passed")

    def authenticate_youtube(self):
        """Authenticate and return a YouTube service object."""
        credentials = None
        pickle_file = os.path.join(tempfile.gettempdir(), "youtube-bulk-upload-token.pickle")

        # Token file stores the user's access and refresh tokens.
        if os.path.exists(pickle_file):
            self.logger.info(f"Existing YouTube auth token file found: {pickle_file}")
            with open(pickle_file, "rb") as token:
                credentials = pickle.load(token)

        # If there are no valid credentials, let the user log in.
        if not credentials or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.youtube_client_secrets_file, scopes=["https://www.googleapis.com/auth/youtube"]
                )
                credentials = flow.run_local_server(port=0)  # This will open a browser for authentication

            # Save the credentials for the next run
            with open(pickle_file, "wb") as token:
                self.logger.info(f"Saving YouTube auth token to file: {pickle_file}")
                pickle.dump(credentials, token)

        return build("youtube", "v3", credentials=credentials)

    def get_channel_id(self):
        youtube = self.authenticate_youtube()

        # Get the authenticated user's channel
        request = youtube.channels().list(part="snippet", mine=True)
        response = request.execute()

        # Extract the channel ID
        if "items" in response:
            channel_id = response["items"][0]["id"]
            return channel_id
        else:
            return None

    def check_if_video_title_exists_on_youtube_channel(self, youtube_title):
        youtube = self.authenticate_youtube()
        channel_id = self.get_channel_id()

        self.logger.info(f"Searching YouTube channel {channel_id} for title: {youtube_title}")
        request = youtube.search().list(part="snippet", channelId=channel_id, q=youtube_title, type="video", maxResults=10)
        response = request.execute()

        # Check if any videos were found
        if "items" in response and len(response["items"]) > 0:
            for item in response["items"]:
                found_title = item["snippet"]["title"]
                similarity_score = fuzz.ratio(youtube_title.lower(), found_title.lower())
                if similarity_score >= 70:  # 70% similarity
                    found_id = item["id"]["videoId"]
                    self.logger.info(
                        f"Potential match found on YouTube channel with ID: {found_id} and title: {found_title} (similarity: {similarity_score}%)"
                    )
                    if self.interactive_prompt:
                        self.logger.debug("Prompting user to confirm whether video matches existing on channel")
                        prompt_message = f"Is '{found_title}' the same video as existing video on channel: '{youtube_title}'? (y/n): "
                        if self.prompt_user_bool(prompt_message):
                            return found_id
                    else:
                        return found_id

        self.logger.info(f"No matching video found with title: {youtube_title}, continuing with upload.")
        return None

    def truncate_to_nearest_word(self, title, max_length):
        self.logger.debug(f"Truncating title with length {len(title)} to nearest word with max length: {max_length}")
        if len(title) <= max_length:
            return title
        truncated_title = title[:max_length].rsplit(" ", 1)[0]
        if len(truncated_title) < max_length:
            truncated_title += " ..."
        return truncated_title

    def upload_video_to_youtube_with_title_thumbnail(self, video_file, youtube_title, youtube_description, thumbnail_filepath):
        self.logger.info(f"Uploading video {video_file} to YouTube with title, description and thumbnail...")
        if self.dry_run:
            self.logger.info(
                f"DRY RUN: Would upload {video_file} to YouTube with title: {youtube_title}, description: {youtube_description[:50]}... and thumbnail: {thumbnail_filepath}"
            )
            return "dry-run-video-id"
        else:
            self.logger.info(f"Authenticating with YouTube...")
            youtube = self.authenticate_youtube()

            body = {
                "snippet": {
                    "title": youtube_title,
                    "description": youtube_description,
                    "tags": self.youtube_keywords,
                    "categoryId": self.youtube_category_id,
                },
                "status": {"privacyStatus": "public"},
            }

            # Use MediaFileUpload to handle the video file
            media_file = MediaFileUpload(video_file, resumable=True)

            # Call the API's videos.insert method to create and upload the video.
            self.logger.info(f"Uploading video to YouTube...")
            request = youtube.videos().insert(part="snippet,status", body=body, media_body=media_file)
            response = request.execute()

            youtube_video_id = response.get("id")
            youtube_url = f"{YOUTUBE_URL_PREFIX}{youtube_video_id}"
            self.logger.info(f"Uploaded video to YouTube: {youtube_url}")

            if thumbnail_filepath is not None:
                media_thumbnail = MediaFileUpload(thumbnail_filepath)
                youtube.thumbnails().set(videoId=youtube_video_id, media_body=media_thumbnail).execute()
                self.logger.info(f"Uploaded thumbnail for video ID {youtube_video_id}")

            return youtube_video_id

    def determine_thumbnail_filepath(self, video_file):
        self.logger.info(f"Determining thumbnail filepath for video file: {video_file}...")

        modified_filename, video_ext = os.path.splitext(video_file)

        # Apply thumbnail filename prefix if set
        if self.thumbnail_filename_prefix is not None:
            modified_filename = f"{self.thumbnail_filename_prefix}{modified_filename}"

        # Apply thumbnail filename suffix if set
        if self.thumbnail_filename_suffix is not None:
            modified_filename = f"{modified_filename}{self.thumbnail_filename_suffix}"

        # Apply thumbnail filename replacements if set
        if self.thumbnail_filename_replacements is not None:
            self.logger.info(f"Applying replacement patterns to thumbnail filename: {modified_filename}")

            for pattern, replacement in self.thumbnail_filename_replacements:
                self.logger.debug(f"Applying thumbnail replacement pattern: {pattern} -> {replacement}")
                modified_filename = re.sub(pattern, replacement, modified_filename)

        # Test each file extension until a file is found
        for ext in self.thumbnail_filename_extensions:
            potential_filename = f"{modified_filename}{ext}"
            if os.path.exists(potential_filename):
                return potential_filename

        if self.interactive_prompt:
            self.logger.debug("Prompting user to confirm whether happy to proceed without thumbnail")
            self.prompt_user_confirmation_or_raise_exception(
                "No valid thumbnail file found. Do you want to continue without a thumbnail?",
                "Operation cancelled due to missing thumbnail file.",
            )

        # If no file is found, return None
        return None

    def determine_youtube_title(self, video_file):
        self.logger.info(f"Crafting YouTube title for video file: {video_file}...")

        video_title, _ = os.path.splitext(video_file)

        # Apply YouTube title prefix if set
        if self.youtube_title_prefix is not None:
            video_title = f"{self.youtube_title_prefix}{video_title}"

        # Apply YouTube title suffix if set
        if self.youtube_title_suffix is not None:
            video_title = f"{video_title}{self.youtube_title_suffix}"

        # Apply YouTube title replacements if set
        if self.youtube_title_replacements is not None:
            self.logger.info(f"Applying replacement patterns to title: {video_title}")

            for pattern, replacement in self.youtube_title_replacements:
                self.logger.debug(f"Applying title replacement pattern: {pattern} -> {replacement}")
                video_title = re.sub(pattern, replacement, video_title)

        # Truncate title to the nearest whole word and add ellipsis if needed
        max_length = 95
        video_title = self.truncate_to_nearest_word(video_title, max_length)

        if self.interactive_prompt:
            self.logger.debug(f"Prompting user to confirm title: {video_title}")
            if not self.prompt_user_bool(f"Are you happy with the generated title: {video_title}?"):
                prompt_message = "Please type the title you would like to use (max 100 chars): "
                video_title = self.prompt_user_text(prompt_message, default_response=video_title)

        return video_title

    def determine_youtube_description(self, video_file, youtube_title):
        self.logger.info(f"Determining YouTube description for video file: {video_file}...")

        description = ""
        if self.youtube_description_template_file is not None:
            with open(self.youtube_description_template_file, "r", encoding="utf-8") as file:
                description = file.read()

        if self.youtube_description_replacements is not None:
            self.logger.info(f"Applying replacement patterns to description text with length: {len(description)}")

            for pattern, replacement in self.youtube_description_replacements:

                # Allow the user to use the jinja-ish syntax to refer to the youtube title in the replacement string
                if "{{youtube_title}}" in replacement:
                    self.logger.debug(f"Replacing youtube title template with actual title: {youtube_title}")
                    replacement = replacement.replace("{{youtube_title}}", youtube_title)

                self.logger.debug(f"Applying description replacement pattern: {pattern} -> {replacement}")
                description = re.sub(pattern, replacement, description)

        if not description and self.interactive_prompt:
            self.logger.warning(f"Unable to load YouTube description from file for video file: {video_file}...")
            prompt_message = "No description template file found. Please type the description you would like to use: "
            description = self.prompt_user_text(prompt_message, default_response=description)

        return description

    def process(self):
        if self.dry_run:
            self.logger.warning("Dry run enabled. No actions will be performed.")

        self.logger.info("Process beginning, validating input parameters")

        # Check required input files and parameters exist before proceeding
        self.validate_input_parameters()

        video_files = self.find_input_files()
        uploaded_videos = []
        for video_file in video_files:
            # Check if stop_event is set before processing each video
            self.logger.debug("Checking stop event before processing videos...")
            if self.stop_event and self.stop_event.is_set():
                self.logger.info("Stop event set, stopping the upload process.")
                break

            if len(uploaded_videos) >= self.upload_batch_limit:
                self.logger.warning(
                    f"Reached the maximum upload limit of {self.upload_batch_limit} videos in a 24-hour period. Please wait until tomorrow to run again."
                )
                break
            try:
                youtube_title = self.determine_youtube_title(video_file)
                youtube_description = self.determine_youtube_description(video_file, youtube_title)
                thumbnail_filepath = self.determine_thumbnail_filepath(video_file)

                existing_video_matching_title_id = self.check_if_video_title_exists_on_youtube_channel(youtube_title)
                if existing_video_matching_title_id is not None:
                    existing_video_matching_title_url = f"{YOUTUBE_URL_PREFIX}{existing_video_matching_title_id}"
                    self.logger.warning(f"Video already exists on YouTube, skipping upload: {existing_video_matching_title_url}")
                    continue

                if self.interactive_prompt:
                    self.logger.info("Interactive prompt is enabled. Confirming upload details with user.")
                    confirmation_prompt = (
                        f"Confirm you are happy for video to be uploaded to your channel with details:\n\n"
                        f"Filename: {video_file}\n\n"
                        f"Title: {youtube_title}?\n\n"
                        f"Thumbnail filepath: {thumbnail_filepath}\n\n"
                        f"Description: {youtube_description}\n\n"
                        "Proceed with upload? (y/n): "
                    )
                    if self.prompt_user_bool(confirmation_prompt):
                        self.logger.info("User confirmed upload details. Proceeding with upload.")
                    else:
                        self.logger.info("User not happy with the upload details. Skipping upload for this video.")
                        continue

                youtube_id = self.upload_video_to_youtube_with_title_thumbnail(
                    video_file, youtube_title, youtube_description, thumbnail_filepath
                )
                uploaded_videos.append(
                    {
                        "input_filename": video_file,
                        "youtube_title": youtube_title,
                        "youtube_id": youtube_id,
                        "youtube_url": f"{YOUTUBE_URL_PREFIX}{youtube_id}",
                    }
                )
            except Exception as e:
                self.logger.error(f"Failed to upload video {video_file} to YouTube: {e}")

        self.logger.debug(f"All videos processed, returning list of uploaded videos")
        return uploaded_videos
