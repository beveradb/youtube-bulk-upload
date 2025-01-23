import logging
import os
from unittest import TestCase
import unittest
from unittest.mock import MagicMock, mock_open, patch
import test_data as td
from youtube_bulk_upload.bulk_upload import (
    YouTubeBulkUpload,
    VideoPrivacyStatus,
    YOUTUBE_URL_PREFIX,
)


class YouTubeBulkUploadAuthenticationTest(TestCase):
    def setUp(self):
        self.logger = logging.getLogger("test_logger")
        self.secrets_file = "mock_secrets.json"
        self.valid_json_content = '{"key": "value"}'
        self.invalid_json_content = '{"key": "value"'

    def test_validate_secrets_file_valid(self):
        # Arrange, Act & Assert
        with (
            patch("builtins.open", mock_open(read_data='{"key": "value"}')),
            patch("os.path.isfile", return_value=True),
        ):
            try:
                YouTubeBulkUpload.validate_secrets_file(self.logger, self.secrets_file)
            except Exception as e:
                self.fail(
                    f"validate_secrets_file raised an exception unexpectedly: {e}"
                )

    def test_validate_secrets_file_invalid_json(self):
        # Arrange, Act & Assert
        with (
            patch("builtins.open", mock_open(read_data='{"key": "value"')),
            patch("os.path.isfile", return_value=True),
        ):
            with self.assertRaises(Exception) as context:
                YouTubeBulkUpload.validate_secrets_file(self.logger, self.secrets_file)
            self.assertIn(
                "YouTube client secrets file is not valid JSON", str(context.exception)
            )

    def test_validate_secrets_file_missing_file(self):
        # Arrange, Act & Assert
        with patch("os.path.isfile", return_value=False):
            with self.assertRaises(Exception) as context:
                YouTubeBulkUpload.validate_secrets_file(self.logger, self.secrets_file)
            self.assertIn(
                "YouTube client secrets file does not exist", str(context.exception)
            )

    def test_authenticate_youtube_with_valid_token(self):
        # Arrange, Act & Assert
        with (
            patch("os.path.exists", return_value=True),
            patch("builtins.open", mock_open(read_data="mock_token_data")),
            patch("pickle.load", return_value=MagicMock(valid=True)),
            patch(
                "youtube_bulk_upload.bulk_upload.build", return_value="YouTubeService"
            ),
        ):
            result = YouTubeBulkUpload.authenticate_youtube(
                self.logger, self.secrets_file
            )
            self.assertEqual(result, "YouTubeService")

    def test_authenticate_youtube_with_new_auth(self):
        # Arrange, Act & Assert
        with (
            patch("os.path.exists", return_value=False),
            patch(
                "youtube_bulk_upload.bulk_upload.YouTubeBulkUpload.open_browser_to_authenticate",
                return_value=MagicMock(),
            ),
            patch("pickle.dump"),
            patch("builtins.open", mock_open()),
            patch(
                "youtube_bulk_upload.bulk_upload.build", return_value="YouTubeService"
            ),
        ):
            result = YouTubeBulkUpload.authenticate_youtube(
                self.logger, self.secrets_file
            )
            self.assertEqual(result, "YouTubeService")


class YouTubeBulkUploadTest(TestCase):
    def setUp(self):
        with (
            patch(
                "youtube_bulk_upload.bulk_upload.YouTubeBulkUpload.validate_secrets_file",
                return_value=None,
            ),
            patch(
                "youtube_bulk_upload.bulk_upload.YouTubeBulkUpload.authenticate_youtube",
                return_value=MagicMock(),
            ),
        ):
            self.sample_uploader = YouTubeBulkUpload(
                youtube_client_secrets_file=td.fake_secrets_file_path,
                logger=td.mock_logger,
                dry_run=False,
                interactive_prompt=True,
                stop_event=None,
                gui=None,
                source_directory=td.folder_path,
                input_file_extensions=[
                    ".mp4",
                    ".mov",
                    ".avi",
                    ".mkv",
                    ".mpg",
                    ".mpeg",
                    ".wmv",
                    ".flv",
                    ".webm",
                    ".m4v",
                    ".vob",
                ],
                upload_batch_limit=100,
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
                privacy_status=VideoPrivacyStatus.PRIVATE.value,
                check_for_duplicate_titles=True,
                progress_callback_func=None,
            )

    def test_find_input_files_raises_Exception_if_no_files_found(self):
        # Arrange, Act & Assert
        with patch("youtube_bulk_upload.bulk_upload.os.listdir", return_value=[]):
            with self.assertRaises(Exception):
                self.sample_uploader.find_input_files()

    def test_find_input_files_raises_Exception_if_folder_contains_invalid_files(self):
        # Arrange, Act & Assert
        with patch(
            "youtube_bulk_upload.bulk_upload.os.listdir",
            return_value=[td.invalid_file_path],
        ):
            with self.assertRaises(Exception):
                self.sample_uploader.find_input_files()

    def test_find_input_files_returns_list_with_files(self):
        # Arrange
        joined_path = os.path.join(td.folder_path, td.valid_video_file_path)
        expected = [joined_path]

        # Act
        with patch(
            "youtube_bulk_upload.bulk_upload.os.listdir",
            return_value=[td.valid_video_file_path],
        ):
            actual_result = self.sample_uploader.find_input_files()

            # Assert
            self.assertListEqual(expected, actual_result)

    def test_prompt_user_confirmation_or_raise_exception_raises_Exception(self):
        # Arrange, Act & Assert
        with patch.object(self.sample_uploader, "prompt_user_bool") as mock_user_bool:
            mock_user_bool.return_value = False
            with self.assertRaises(Exception) as context:
                self.sample_uploader.prompt_user_confirmation_or_raise_exception(
                    td.sample_prompt, td.sample_exit_message
                )
                self.assertIn(
                    td.sample_exit_message,
                    str(context.exception),
                )

    def test_prompt_user_confirmation_or_raise_exception_returns_None_if_user_bool_is_True(
        self,
    ):
        # Arrange, Act
        with patch.object(self.sample_uploader, "prompt_user_bool") as mock_user_bool:
            mock_user_bool.return_value = True
            actual_result = (
                self.sample_uploader.prompt_user_confirmation_or_raise_exception(
                    td.sample_prompt, td.sample_exit_message
                )
            )
        # Assert
        self.assertIsNone(actual_result)

    def test_prompt_user_bool_gui_accepts_prompt(self):
        # Arrange
        self.sample_uploader.gui = MagicMock()
        self.sample_uploader.gui.user_input_result = True
        self.sample_uploader.gui.user_input_event = MagicMock()

        # Act
        with (
            patch.object(self.sample_uploader.gui, "prompt_user_bool") as mock_prompt,
            patch.object(
                self.sample_uploader.gui.user_input_event, "wait"
            ) as mock_wait,
        ):
            result = self.sample_uploader.prompt_user_bool("Sample message")

            # Assert
            self.assertTrue(result)
            mock_prompt.assert_called_once_with(
                prompt_message="Sample message", allow_empty=False
            )
            mock_wait.assert_called_once()

    def test_prompt_user_bool_gui_rejects_prompt(self):
        # Arrange
        self.sample_uploader.gui = MagicMock()
        self.sample_uploader.gui.user_input_result = False
        self.sample_uploader.gui.user_input_event = MagicMock()

        # Act
        with (
            patch.object(self.sample_uploader.gui, "prompt_user_bool") as mock_prompt,
            patch.object(
                self.sample_uploader.gui.user_input_event, "wait"
            ) as mock_wait,
        ):
            result = self.sample_uploader.prompt_user_bool("Sample message")

            # Assert
            self.assertFalse(result)
            mock_prompt.assert_called_once_with(
                prompt_message="Sample message", allow_empty=False
            )
            mock_wait.assert_called_once()

    def test_prompt_user_bool_cli_accepts_prompt(self):
        # Act
        with patch("builtins.input", return_value="y") as mock_input:
            result = self.sample_uploader.prompt_user_bool("Sample message")

            # Assert
            self.assertTrue(result)
            mock_input.assert_called_once_with("Sample message y/[n] ")

    def test_prompt_user_bool_cli_rejects_prompt(self):
        # Act
        with patch("builtins.input", return_value="n") as mock_input:
            result = self.sample_uploader.prompt_user_bool("Sample message")

            # Assert
            self.assertFalse(result)
            mock_input.assert_called_once_with("Sample message y/[n] ")

    def test_prompt_user_bool_cli_empty_input_allowed(self):
        # Act
        with patch("builtins.input", return_value="") as mock_input:
            result = self.sample_uploader.prompt_user_bool(
                "Sample message", allow_empty=True
            )

            # Assert
            self.assertTrue(result)
            mock_input.assert_called_once_with("Sample message [y]/n ")

    def test_prompt_user_bool_cli_invalid_input(self):
        # Arrange
        with (
            patch("builtins.input", side_effect=["invalid", "y"]) as mock_input,
            patch("builtins.print"),
        ):
            # Act
            result = self.sample_uploader.prompt_user_bool("Sample message")

            # Assert
            self.assertFalse(result)
            self.assertEqual(mock_input.call_count, 1)
            mock_input.assert_called_with("Sample message y/[n] ")

    def test_prompt_user_text_gui_returns_user_input(self):
        # Arrange
        self.sample_uploader.gui = MagicMock()
        self.sample_uploader.gui.user_input_result = "User Input"
        self.sample_uploader.gui.user_input_event = MagicMock()

        # Act
        with (
            patch.object(self.sample_uploader.gui, "prompt_user_text") as mock_prompt,
            patch.object(
                self.sample_uploader.gui.user_input_event, "wait"
            ) as mock_wait,
        ):
            result = self.sample_uploader.prompt_user_text("Sample message")

            # Assert
            self.assertEqual(result, "User Input")
            mock_prompt.assert_called_once_with("Sample message", "")
            mock_wait.assert_called_once()

    def test_prompt_user_text_cli_returns_user_input(self):
        # Act
        with patch("builtins.input", return_value="CLI Input") as mock_input:
            result = self.sample_uploader.prompt_user_text("Sample message")

            # Assert
            self.assertEqual(result, "CLI Input")
            mock_input.assert_called_once_with("Sample message")

    def test_validate_input_parameters_no_description_template(self):
        # Arrange
        self.sample_uploader.youtube_description_template_file = None

        # Act
        with (
            patch.object(self.sample_uploader.logger, "info") as mock_info,
            patch.object(self.sample_uploader.logger, "warning") as mock_warning,
        ):
            self.sample_uploader.validate_input_parameters()

            # Assert
            mock_info.assert_any_call(
                "Validating input parameters for enabled features..."
            )
            mock_info.assert_any_call(f"Current directory to process: {os.getcwd()}")
            mock_warning.assert_called_once_with(
                "No YouTube description template file provided. Description will be empty unless entered interactively."
            )

    def test_validate_input_parameters_with_nonexistent_description_file_raises_exception(
        self,
    ):
        # Arrange
        self.sample_uploader.youtube_description_template_file = td.invalid_file_path

        # Act & Assert
        with (
            patch("os.path.isfile", return_value=False) as mock_isfile,
            patch.object(self.sample_uploader.logger, "info") as mock_info,
        ):
            with self.assertRaises(Exception) as context:
                self.sample_uploader.validate_input_parameters()

            # Assert
            mock_isfile.assert_called_once_with(td.invalid_file_path)
            mock_info.assert_any_call(f"Current directory to process: {os.getcwd()}")
            self.assertIn(
                "YouTube description file does not exist", str(context.exception)
            )

    def test_validate_input_parameters_with_valid_description_file(self):
        # Arrange
        self.sample_uploader.youtube_description_template_file = (
            td.valid_video_file_path
        )

        # Act
        with (
            patch("os.path.isfile", return_value=True) as mock_isfile,
            patch.object(self.sample_uploader.logger, "info") as mock_info,
        ):
            self.sample_uploader.validate_input_parameters()

            # Assert
            mock_isfile.assert_called_once_with(td.valid_video_file_path)
            mock_info.assert_any_call(
                f"YouTube description template file exists: {td.valid_video_file_path}"
            )

    def test_validate_input_parameters_invalid_privacy_status_raises_exception(self):
        # Arrange
        self.sample_uploader.privacy_status = "invalid_status"

        # Act & Assert
        with patch.object(self.sample_uploader.logger, "info") as mock_info:
            with self.assertRaises(Exception) as context:
                self.sample_uploader.validate_input_parameters()

            # Assert
            self.assertIn(
                '"invalid_status" is not a valid video privacy value',
                str(context.exception),
            )
            mock_info.assert_any_call(
                "Validating input parameters for enabled features..."
            )

    def test_validate_input_parameters_valid_privacy_status(self):
        # Arrange
        self.sample_uploader.privacy_status = VideoPrivacyStatus.PRIVATE.value

        # Act
        with (
            patch.object(self.sample_uploader.logger, "debug") as mock_debug,
            patch("os.path.isfile", return_value=True),
        ):
            self.sample_uploader.youtube_description_template_file = (
                "/path/to/existing_file.txt"
            )
            self.sample_uploader.validate_input_parameters()

            # Assert
            mock_debug.assert_any_call("YouTube upload checks passed")

    def test_get_channel_id_returns_valid_id(self):
        # Arrange & Act
        with patch.object(
            self.sample_uploader.youtube.channels().list(),
            "execute",
            return_value=td.mock_channel_response,
        ) as mock_execute:
            result = self.sample_uploader.get_channel_id()

            # Assert
            self.assertEqual(result, td.mock_channel_id)
            mock_execute.assert_called_once()

    def test_get_channel_id_returns_none_when_no_items(self):
        # Arrange
        mock_response = {}

        # Act
        with patch.object(
            self.sample_uploader.youtube.channels().list(),
            "execute",
            return_value=mock_response,
        ) as mock_execute:
            result = self.sample_uploader.get_channel_id()

            # Assert
            self.assertIsNone(result)
            mock_execute.assert_called_once()

    def test_check_if_video_title_exists_on_youtube_channel_finds_match(self):
        # Arrange
        self.sample_uploader.interactive_prompt = False

        # Act
        with (
            patch.object(
                self.sample_uploader, "get_channel_id", return_value=td.mock_channel_id
            ) as mock_get_channel_id,
            patch.object(
                self.sample_uploader.youtube.search().list(),
                "execute",
                return_value=td.mock_video_response,
            ) as mock_execute,
            patch.object(self.sample_uploader.logger, "info") as mock_info,
        ):
            result = (
                self.sample_uploader.check_if_video_title_exists_on_youtube_channel(
                    td.sample_video_title
                )
            )

            # Assert
            self.assertEqual(result, td.sample_video_id)
            mock_get_channel_id.assert_called_once()
            mock_execute.assert_called_once()
            mock_info.assert_any_call(
                f"Searching YouTube channel {td.mock_channel_id} for title: {td.sample_video_title}"
            )

    def test_check_if_video_title_exists_on_youtube_channel_no_match(self):
        # Arrange
        self.sample_uploader.interactive_prompt = False

        # Act
        with (
            patch.object(
                self.sample_uploader, "get_channel_id", return_value=td.mock_channel_id
            ) as mock_get_channel_id,
            patch.object(
                self.sample_uploader.youtube.search().list(),
                "execute",
                return_value=td.mock_empty_response,
            ) as mock_execute,
            patch.object(self.sample_uploader.logger, "info") as mock_info,
        ):
            result = (
                self.sample_uploader.check_if_video_title_exists_on_youtube_channel(
                    "Non-Existent Title"
                )
            )

            # Assert
            self.assertIsNone(result)
            mock_get_channel_id.assert_called_once()
            mock_execute.assert_called_once()
            mock_info.assert_any_call(
                f"Searching YouTube channel {td.mock_channel_id} for title: Non-Existent Title"
            )
            mock_info.assert_any_call(
                "No matching video found with title: Non-Existent Title, continuing with upload."
            )

    def test_check_if_video_title_exists_on_youtube_channel_interactive_prompt_accepts(
        self,
    ):
        # Arrange
        self.sample_uploader.interactive_prompt = True

        # Act
        with (
            patch.object(
                self.sample_uploader, "get_channel_id", return_value=td.mock_channel_id
            ) as mock_get_channel_id,
            patch.object(
                self.sample_uploader.youtube.search().list(),
                "execute",
                return_value=td.mock_video_response,
            ) as mock_execute,
            patch.object(
                self.sample_uploader, "prompt_user_bool", return_value=True
            ) as mock_prompt,
            patch.object(self.sample_uploader.logger, "info") as mock_info,
        ):
            result = (
                self.sample_uploader.check_if_video_title_exists_on_youtube_channel(
                    td.sample_video_title
                )
            )

            # Assert
            self.assertEqual(result, td.sample_video_id)
            mock_get_channel_id.assert_called_once()
            mock_execute.assert_called_once()
            mock_prompt.assert_called_once_with(
                f"Is '{td.sample_video_title}' the same video as existing video on channel: '{td.sample_video_title}'? (y/n): "
            )
            mock_info.assert_any_call(
                f"Searching YouTube channel {td.mock_channel_id} for title: {td.sample_video_title}"
            )

    def test_check_if_video_title_exists_on_youtube_channel_interactive_prompt_rejects(
        self,
    ):
        # Arrange
        self.sample_uploader.interactive_prompt = True

        # Act
        with (
            patch.object(
                self.sample_uploader, "get_channel_id", return_value=td.mock_channel_id
            ) as mock_get_channel_id,
            patch.object(
                self.sample_uploader.youtube.search().list(),
                "execute",
                return_value=td.mock_video_response,
            ) as mock_execute,
            patch.object(
                self.sample_uploader, "prompt_user_bool", return_value=False
            ) as mock_prompt,
            patch.object(self.sample_uploader.logger, "info") as mock_info,
        ):
            result = (
                self.sample_uploader.check_if_video_title_exists_on_youtube_channel(
                    td.sample_video_title
                )
            )

            # Assert
            self.assertIsNone(result)
            mock_get_channel_id.assert_called_once()
            mock_execute.assert_called_once()
            mock_prompt.assert_called_once_with(
                f"Is '{td.sample_video_title}' the same video as existing video on channel: '{td.sample_video_title}'? (y/n): "
            )
            mock_info.assert_any_call(
                f"Searching YouTube channel {td.mock_channel_id} for title: {td.sample_video_title}"
            )

    def test_truncate_to_nearest_word_within_limit(self):
        # Arrange
        title = td.sample_video_title
        max_length = len(title) + 1

        # Act
        with patch.object(self.sample_uploader.logger, "debug") as mock_debug:
            result = self.sample_uploader.truncate_to_nearest_word(title, max_length)

            # Assert
            self.assertEqual(result, title)
            mock_debug.assert_called_once_with(
                f"Truncating title with length {len(title)} to nearest word with max length: {max_length}"
            )

    def test_truncate_to_nearest_word_exceeds_limit(self):
        # Arrange
        title = td.sample_video_title
        max_length = len(title) - 1

        # Act
        with patch.object(self.sample_uploader.logger, "debug") as mock_debug:
            result = self.sample_uploader.truncate_to_nearest_word(title, max_length)

            # Assert
            expected = "Sample Video ..."
            self.assertEqual(result, expected)
            mock_debug.assert_called_once_with(
                f"Truncating title with length {len(title)} to nearest word with max length: {max_length}"
            )

    def test_truncate_to_nearest_word_exact_boundary(self):
        # Arrange
        title = td.sample_video_title
        max_length = len(title)

        # Act
        with patch.object(self.sample_uploader.logger, "debug") as mock_debug:
            result = self.sample_uploader.truncate_to_nearest_word(title, max_length)

            # Assert
            self.assertEqual(result, title)
            mock_debug.assert_called_once_with(
                f"Truncating title with length {len(title)} to nearest word with max length: {max_length}"
            )

    def test_upload_video_to_youtube_with_title_thumbnail_dry_run(self):
        # Arrange
        self.sample_uploader.dry_run = True

        # Act
        with patch.object(self.sample_uploader.logger, "info") as mock_info:
            result = self.sample_uploader.upload_video_to_youtube_with_title_thumbnail(
                td.valid_video_file_path,
                td.sample_video_title,
                td.sample_description,
                td.thumbnail_filepath,
            )

            # Assert
            self.assertEqual(result, "dry-run-video-id")
            mock_info.assert_any_call(
                f"DRY RUN: Would upload {td.valid_video_file_path} to YouTube with title: {td.sample_video_title}, "
                f"description: {td.sample_description[:50]}... and thumbnail: {td.thumbnail_filepath} "
                f"with Privacy Status: {self.sample_uploader.privacy_status}"
            )

    def test_upload_video_to_youtube_with_title_thumbnail_actual_upload(self):
        # Arrange
        self.sample_uploader.dry_run = False

        # Act
        with (
            patch("youtube_bulk_upload.bulk_upload.MediaFileUpload") as mock_media_file,
            patch.object(
                self.sample_uploader.youtube.videos().insert(),
                "next_chunk",
                side_effect=[(None, td.mock_mediaFileUpload_response)],
            ) as mock_next_chunk,
            patch.object(self.sample_uploader.logger, "info") as mock_info,
            patch.object(
                self.sample_uploader.youtube.thumbnails().set(), "execute"
            ) as mock_thumbnail_set,
        ):
            result = self.sample_uploader.upload_video_to_youtube_with_title_thumbnail(
                td.valid_video_file_path,
                td.sample_video_title,
                td.sample_description,
                td.thumbnail_filepath,
            )

            # Assert
            self.assertEqual(result, td.sample_video_id)
            mock_media_file.assert_any_call(
                td.valid_video_file_path, resumable=True, chunksize=td.sample_chunk_size
            )
            mock_next_chunk.assert_called_once()
            mock_info.assert_any_call(
                f"Uploaded video to YouTube: {YOUTUBE_URL_PREFIX}{td.sample_video_id}"
            )
            mock_thumbnail_set.assert_called_once()

    def test_upload_video_to_youtube_with_title_thumbnail_no_thumbnail(self):
        # Arrange
        self.sample_uploader.dry_run = False

        # Act
        with (
            patch("youtube_bulk_upload.bulk_upload.MediaFileUpload") as mock_media_file,
            patch.object(
                self.sample_uploader.youtube.videos().insert(),
                "next_chunk",
                side_effect=[(None, td.mock_mediaFileUpload_response)],
            ) as mock_next_chunk,
            patch.object(self.sample_uploader.logger, "info") as mock_info,
        ):
            result = self.sample_uploader.upload_video_to_youtube_with_title_thumbnail(
                td.valid_video_file_path,
                td.sample_video_title,
                td.sample_description,
                None,
            )

            # Assert
            self.assertEqual(result, td.sample_video_id)
            mock_media_file.assert_any_call(
                td.valid_video_file_path, resumable=True, chunksize=td.sample_chunk_size
            )
            mock_next_chunk.assert_called_once()
            mock_info.assert_any_call(
                f"Uploaded video to YouTube: {YOUTUBE_URL_PREFIX}{td.sample_video_id}"
            )

    def test_determine_thumbnail_filepath_finds_existing_file(self):
        # Arrange
        expected_thumbnail = f"{td.valid_video_file_path}.png"
        self.sample_uploader.thumbnail_filename_extensions = [".png", ".jpg"]
        self.sample_uploader.thumbnail_filename_replacements = None
        self.sample_uploader.interactive_prompt = False

        # Act
        with (
            patch("os.path.exists", side_effect=lambda _: True) as mock_exists,
            patch.object(self.sample_uploader.logger, "info") as mock_info,
        ):
            result = self.sample_uploader.determine_thumbnail_filepath(
                td.valid_video_file_path
            )

            # Assert
            self.assertEqual(result, expected_thumbnail)
            mock_exists.assert_any_call(expected_thumbnail)
            mock_info.assert_called_with(
                f"Determining thumbnail filepath for video file: {td.valid_video_file_path}..."
            )

    def test_determine_thumbnail_filepath_no_matching_file_prompts_user(self):
        # Arrange
        self.sample_uploader.thumbnail_filename_extensions = [".png"]
        self.sample_uploader.interactive_prompt = True

        # Act
        with (
            patch("os.path.exists", return_value=False) as mock_exists,
            patch.object(self.sample_uploader.logger, "info") as mock_info,
            patch.object(
                self.sample_uploader, "prompt_user_confirmation_or_raise_exception"
            ) as mock_prompt,
        ):
            result = self.sample_uploader.determine_thumbnail_filepath(
                td.valid_video_file_path
            )

            # Assert
            self.assertIsNone(result)
            mock_exists.assert_called_once()
            mock_info.assert_called_with(
                f"Determining thumbnail filepath for video file: {td.valid_video_file_path}..."
            )
            mock_prompt.assert_called_once_with(
                "No valid thumbnail file found. Do you want to continue without a thumbnail?",
                "Operation cancelled due to missing thumbnail file.",
            )

    def test_determine_youtube_title_applies_prefix_suffix_and_truncates(self):
        # Arrange
        self.sample_uploader.youtube_title_prefix = "Prefix: "
        self.sample_uploader.youtube_title_suffix = " :Suffix"
        self.sample_uploader.youtube_title_replacements = [(r"video", "clip")]
        self.sample_uploader.interactive_prompt = False
        # Act
        with (
            patch.object(
                self.sample_uploader,
                "truncate_to_nearest_word",
                return_value=td.sample_video_title,
            ) as mock_truncate,
            patch.object(self.sample_uploader.logger, "info") as mock_info,
            patch.object(self.sample_uploader.logger, "debug") as mock_debug,
        ):
            patch.object(self.sample_uploader, "prompt_user_bool", return_value=True)
            result = self.sample_uploader.determine_youtube_title(td.sample_video_file)

            # Assert
            self.assertEqual(result, td.sample_video_title)
            mock_truncate.assert_called_once_with("Prefix: clip :Suffix", 95)
            mock_info.assert_any_call(
                f"Crafting YouTube title for video file: {td.sample_video_file}..."
            )
            mock_debug.assert_any_call(
                "Applying title replacement pattern: video -> clip"
            )

    def test_determine_youtube_title_interactive_prompt_accepts_title(self):
        # Arrange
        self.sample_uploader.interactive_prompt = True

        # Act
        with (
            patch.object(
                self.sample_uploader, "prompt_user_bool", return_value=True
            ) as mock_prompt,
            patch.object(self.sample_uploader.logger, "debug") as mock_debug,
        ):
            result = self.sample_uploader.determine_youtube_title(td.sample_video_file)

            # Assert
            self.assertEqual(result, "video")
            mock_prompt.assert_called_once_with(
                "Are you happy with the generated title: video?"
            )
            mock_debug.assert_called_with("Prompting user to confirm title: video")

    def test_determine_youtube_description_applies_replacements(self):
        # Arrange
        self.sample_uploader.youtube_description_template_file = "template.txt"
        self.sample_uploader.youtube_description_replacements = [
            ("{{youtube_title}}", "Replaced Title")
        ]

        template_content = "This is the description with {{youtube_title}}."

        # Act
        with (
            patch("builtins.open", mock_open(read_data=template_content)) as mock_file,
            patch.object(self.sample_uploader.logger, "info") as mock_info,
            patch.object(self.sample_uploader.logger, "debug") as mock_debug,
        ):
            result = self.sample_uploader.determine_youtube_description(
                td.sample_video_file, td.sample_video_title
            )

            # Assert
            self.assertEqual(result, "This is the description with Replaced Title.")
            mock_file.assert_called_once_with("template.txt", "r", encoding="utf-8")
            mock_info.assert_any_call(
                "Determining YouTube description for video file: video.mp4..."
            )
            mock_debug.assert_any_call(
                "Applying description replacement pattern: {{youtube_title}} -> Replaced Title"
            )

    def test_determine_youtube_description_prompts_user_when_no_template(self):
        # Arrange
        self.sample_uploader.youtube_description_template_file = None
        self.sample_uploader.interactive_prompt = True

        # Act
        with (
            patch.object(self.sample_uploader.logger, "warning") as mock_warning,
            patch.object(
                self.sample_uploader,
                "prompt_user_text",
                return_value=td.sample_description,
            ) as mock_prompt,
        ):
            result = self.sample_uploader.determine_youtube_description(
                td.sample_video_file, td.sample_video_title
            )

            # Assert
            self.assertEqual(result, td.sample_description)
            mock_warning.assert_called_once_with(
                f"Unable to load YouTube description from file for video file: {td.sample_video_file}..."
            )
            mock_prompt.assert_called_once_with(
                "No description template file found. Please type the description you would like to use: ",
                default_response="",
            )

    def test_process_dry_run_logs_warning_and_returns_empty_list(self):
        # Arrange
        self.sample_uploader.dry_run = True

        # Act
        with (
            patch.object(self.sample_uploader.logger, "warning") as mock_warning,
            patch.object(
                self.sample_uploader, "validate_input_parameters"
            ) as mock_validate,
            patch.object(self.sample_uploader, "find_input_files", return_value=[]),
        ):
            result = self.sample_uploader.process()

            # Assert
            self.assertEqual(result, [])
            mock_warning.assert_called_once_with(
                "Dry run enabled. No actions will be performed."
            )
            mock_validate.assert_called_once()

    def test_process_stops_on_stop_event(self):
        # Arrange
        self.sample_uploader.stop_event = MagicMock(is_set=MagicMock(return_value=True))
        self.sample_uploader.upload_batch_limit = 10

        # Act
        with (
            patch.object(
                self.sample_uploader, "validate_input_parameters"
            ) as mock_validate,
            patch.object(
                self.sample_uploader,
                "find_input_files",
                return_value=["video1.mp4", "video2.mp4"],
            ) as mock_find,
            patch.object(self.sample_uploader.logger, "info") as mock_info,
        ):
            result = self.sample_uploader.process()

            # Assert
            self.assertEqual(result, [])
            mock_validate.assert_called_once()
            mock_find.assert_called_once()
            mock_info.assert_any_call("Stop event set, stopping the upload process.")

    def test_process_skips_duplicates(self):
        # Arrange
        self.sample_uploader.check_for_duplicate_titles = True

        # Act
        with (
            patch.object(
                self.sample_uploader, "validate_input_parameters"
            ) as mock_validate,
            patch.object(
                self.sample_uploader,
                "find_input_files",
                return_value=[td.sample_video_file],
            ) as mock_find,
            patch.object(
                self.sample_uploader,
                "determine_youtube_title",
                return_value=td.sample_video_title,
            ) as mock_title,
            patch.object(
                self.sample_uploader,
                "check_if_video_title_exists_on_youtube_channel",
                return_value="existing_video_id",
            ) as mock_check,
            patch.object(
                self.sample_uploader,
                "prompt_user_text",
                return_value=td.sample_description,
            ),
            patch.object(
                self.sample_uploader,
                "determine_thumbnail_filepath",
                return_value=td.sample_video_file,
            ),
            patch.object(self.sample_uploader.logger, "warning") as mock_warning,
        ):
            result = self.sample_uploader.process()

            # Assert
            self.assertEqual(result, [])
            mock_validate.assert_called_once()
            mock_find.assert_called_once()
            mock_title.assert_called_once_with(td.sample_video_file)
            mock_check.assert_called_once_with(td.sample_video_title)
            mock_warning.assert_called_with(
                f"Video already exists on YouTube, skipping upload: {YOUTUBE_URL_PREFIX}existing_video_id"
            )

    def test_process_interactive_prompt_skips_video_on_rejection(self):
        # Arrange
        self.sample_uploader.interactive_prompt = True

        # Act
        with (
            patch.object(
                self.sample_uploader, "validate_input_parameters"
            ) as mock_validate,
            patch.object(
                self.sample_uploader, "find_input_files", return_value=[td.sample_video_file]
            ) as mock_find,
            patch.object(
                self.sample_uploader,
                "determine_youtube_title",
                return_value=td.sample_video_title,
            ) as mock_title,
            patch.object(
                self.sample_uploader,
                "determine_youtube_description",
                return_value=td.sample_description,
            ) as mock_description,
            patch.object(
                self.sample_uploader,
                "determine_thumbnail_filepath",
                return_value=td.thumbnail_filepath,
            ) as mock_thumbnail,
            patch.object(
                self.sample_uploader, "prompt_user_bool", return_value=False
            ) as mock_prompt,
            patch.object(self.sample_uploader.logger, "info") as mock_info,
        ):
            result = self.sample_uploader.process()

            # Assert
            self.assertEqual(result, [])
            mock_validate.assert_called_once()
            mock_find.assert_called_once()
            mock_title.assert_called_once_with(td.sample_video_file)
            mock_description.assert_called_once_with(td.sample_video_file, td.sample_video_title)
            mock_thumbnail.assert_called_once_with(td.sample_video_file)
            mock_prompt.assert_called_once()
            mock_info.assert_any_call(
                "User not happy with the upload details. Skipping upload for this video."
            )

    def test_process_uploads_videos_successfully(self):
        # Arrange
        self.sample_uploader.check_for_duplicate_titles = False

        # Act
        with (
            patch.object(
                self.sample_uploader, "validate_input_parameters"
            ) as mock_validate,
            patch.object(
                self.sample_uploader, "find_input_files", return_value=[td.sample_video_file]
            ) as mock_find,
            patch.object(
                self.sample_uploader,
                "determine_youtube_title",
                return_value=td.sample_video_title,
            ) as mock_title,
            patch.object(
                self.sample_uploader,
                "determine_youtube_description",
                return_value=td.sample_description,
            ) as mock_description,
            patch.object(
                self.sample_uploader,
                "determine_thumbnail_filepath",
                return_value=td.thumbnail_filepath,
            ) as mock_thumbnail,
            patch.object(
                self.sample_uploader,
                "prompt_user_bool",
                return_value=True,
            ),
            patch.object(
                self.sample_uploader,
                "upload_video_to_youtube_with_title_thumbnail",
                return_value=td.sample_video_id,
            ) as mock_upload,
            patch.object(self.sample_uploader.logger, "info"),
        ):
            result = self.sample_uploader.process()

            # Assert
            expected_result = [
                {
                    "input_filename": td.sample_video_file,
                    "youtube_title": td.sample_video_title,
                    "youtube_id": td.sample_video_id,
                    "youtube_url": f"{YOUTUBE_URL_PREFIX}{td.sample_video_id}",
                }
            ]
            self.assertEqual(result, expected_result)
            mock_validate.assert_called_once()
            mock_find.assert_called_once()
            mock_title.assert_called_once_with(td.sample_video_file)
            mock_description.assert_called_once_with(td.sample_video_file, td.sample_video_title)
            mock_thumbnail.assert_called_once_with(td.sample_video_file)
            mock_upload.assert_called_once_with(
                td.sample_video_file, td.sample_video_title, td.sample_description, td.thumbnail_filepath
            )


if __name__ == "__main__":
    unittest.main()
