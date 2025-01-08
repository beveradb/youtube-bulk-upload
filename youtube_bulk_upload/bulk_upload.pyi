from enum import Enum
from logging import Logger, Formatter
from typing import Any, Iterable
from google.auth.external_account_authorized_user import Credentials as Creds
from google.oauth2.credentials import Credentials

YOUTUBE_URL_PREFIX: str
DEFAULT_LOG_LEVEL: int
DEFAULT_LOGGING_FORMATTER: Formatter

class VideoPrivacyStatus(Enum):
    PUBLIC = "public"
    PRIVATE = "private"
    UNLISTED = "unlisted"

class YouTubeBulkUpload:
    logger: Logger | None
    gui: Any | None
    stop_event: Any | None
    dry_run: bool
    source_directory: str
    input_file_extensions: Iterable[str]
    youtube_client_secrets_file: str
    youtube_category_id: str
    youtube_keywords: Iterable[str]
    youtube_description_template_file: str | None
    youtube_description_replacements: str | None
    youtube_title_prefix: str | None
    youtube_title_suffix: str | None
    youtube_title_replacements: Iterable[Iterable[str]]
    thumbnail_filename_prefix: str | None
    thumbnail_filename_suffix: str | None
    thumbnail_filename_replacements: Iterable[Iterable[str]] | None
    thumbnail_filename_extensions: Iterable[str]
    privacy_status: str
    interactive_prompt: bool
    upload_batch_limit: int
    check_for_duplicate_titles: bool
    progress_callback_func: Any | None
    def __init__(
        self,
        youtube_client_secrets_file: str,
        logger: Logger | None = ...,
        dry_run: bool = ...,
        interactive_prompt: bool = ...,
        stop_event: Any | None = ...,
        gui: Any | None = ...,
        source_directory: str = ...,
        input_file_extensions: Iterable[str] = ...,
        upload_batch_limit: int = ...,
        youtube_category_id: str = ...,
        youtube_keywords: Iterable[str] = ...,
        youtube_description_template_file: str | None = ...,
        youtube_description_replacements: str | None = ...,
        youtube_title_prefix: str | None = ...,
        youtube_title_suffix: str | None = ...,
        youtube_title_replacements: Iterable[Iterable[str]] | None = ...,
        thumbnail_filename_prefix: str | None = ...,
        thumbnail_filename_suffix: str | None = ...,
        thumbnail_filename_replacements: Iterable[Iterable[str]] | None = ...,
        thumbnail_filename_extensions: Iterable[str] = ...,
        privacy_status: str = ...,
        check_for_duplicate_titles: bool = ...,
        progress_callback_func: Any | None = ...,
    ) -> None: ...
    def find_input_files(self) -> list[str]: ...
    def prompt_user_confirmation_or_raise_exception(
        self, prompt_message, exit_message, allow_empty: bool = ...
    ) -> None: ...
    def prompt_user_bool(self, prompt_message, allow_empty: bool = ...) -> bool: ...
    def prompt_user_text(self, prompt_message, default_response: str = ...) -> str: ...
    def validate_input_parameters(self) -> None: ...
    @classmethod
    def validate_secrets_file(cls, logger: Logger, secrets_file: str) -> None: ...
    @classmethod
    def authenticate_youtube(cls, logger: Logger, youtube_client_secrets_file: str): ...
    @classmethod
    def open_browser_to_authenticate(cls, secrets_file: str) -> Credentials | Creds: ...
    def get_channel_id(self) -> str | None: ...
    def check_if_video_title_exists_on_youtube_channel(
        self, youtube_title
    ) -> str | None: ...
    def truncate_to_nearest_word(self, title, max_length) -> str: ...
    def upload_video_to_youtube_with_title_thumbnail(
        self, video_file, youtube_title, youtube_description, thumbnail_filepath
    ) -> str: ...
    def determine_thumbnail_filepath(self, video_file) -> str | None: ...
    def determine_youtube_title(self, video_file) -> str: ...
    def determine_youtube_description(self, video_file, youtube_title) -> str: ...
    def process(self) -> list[dict[str, str]]: ...
