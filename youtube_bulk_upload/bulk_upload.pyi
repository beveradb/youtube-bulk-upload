from enum import Enum
from logging import Logger, Formatter
from typing import Any, Iterable, Optional, Union
from google.auth.external_account_authorized_user import Credentials as Creds
from google.oauth2.credentials import Credentials

OPTIONAL_ANY = Optional[Any]
OPTIONAL_STR = Optional[str]

YOUTUBE_URL_PREFIX: str
DEFAULT_LOG_LEVEL: int
DEFAULT_LOGGING_FORMATTER: Formatter

class VideoPrivacyStatus(Enum):
    PUBLIC = "public"
    PRIVATE = "private"
    UNLISTED = "unlisted"

class YouTubeBulkUpload:
    logger: Optional[Logger]
    youtube: Any
    gui: OPTIONAL_ANY
    stop_event: OPTIONAL_ANY
    dry_run: bool
    source_directory: str
    input_file_extensions: Iterable[str]
    youtube_category_id: str
    youtube_keywords: Iterable[str]
    youtube_description_template_file: OPTIONAL_STR
    youtube_description_replacements: Optional[Iterable[Iterable[str]]]
    youtube_title_prefix: OPTIONAL_STR
    youtube_title_suffix: OPTIONAL_STR
    youtube_title_replacements: Iterable[Iterable[str]]
    thumbnail_filename_prefix: OPTIONAL_STR
    thumbnail_filename_suffix: OPTIONAL_STR
    thumbnail_filename_replacements: Optional[Iterable[Iterable[str]]]
    thumbnail_filename_extensions: Iterable[str]
    privacy_status: str
    interactive_prompt: bool
    upload_batch_limit: int
    check_for_duplicate_titles: bool
    progress_callback_func: OPTIONAL_ANY
    def __init__(
        self,
        youtube_client_secrets_file: str,
        logger: Optional[Logger] = ...,
        dry_run: bool = ...,
        interactive_prompt: bool = ...,
        stop_event: OPTIONAL_ANY = ...,
        gui: OPTIONAL_ANY = ...,
        source_directory: str = ...,
        input_file_extensions: Iterable[str] = ...,
        upload_batch_limit: int = ...,
        youtube_category_id: str = ...,
        youtube_keywords: Iterable[str] = ...,
        youtube_description_template_file: OPTIONAL_STR = ...,
        youtube_description_replacements: OPTIONAL_STR = ...,
        youtube_title_prefix: OPTIONAL_STR = ...,
        youtube_title_suffix: OPTIONAL_STR = ...,
        youtube_title_replacements: Optional[Iterable[Iterable[str]]] = ...,
        thumbnail_filename_prefix: OPTIONAL_STR = ...,
        thumbnail_filename_suffix: OPTIONAL_STR = ...,
        thumbnail_filename_replacements: Optional[Iterable[Iterable[str]]] = ...,
        thumbnail_filename_extensions: Iterable[str] = ...,
        privacy_status: str = ...,
        check_for_duplicate_titles: bool = ...,
        progress_callback_func: OPTIONAL_ANY = ...,
    ) -> None: ...
    def find_input_files(self) -> list[str]: ...
    def prompt_user_confirmation_or_raise_exception(
        self, prompt_message: str, exit_message: str, allow_empty: bool = ...
    ) -> None: ...
    def prompt_user_bool(self, prompt_message: str, allow_empty: bool = ...) -> bool: ...
    def prompt_user_text(self, prompt_message: str, default_response: str = ...) -> str: ...
    def validate_input_parameters(self) -> None: ...
    @classmethod
    def validate_secrets_file(cls, logger: Logger, secrets_file: str) -> None: ...
    @classmethod
    def authenticate_youtube(cls, logger: Logger, youtube_client_secrets_file: str) -> Any: ...
    @classmethod
    def open_browser_to_authenticate(cls, secrets_file: str) -> Union[Credentials, Creds]: ...
    def get_channel_id(self) -> OPTIONAL_STR: ...
    def check_if_video_title_exists_on_youtube_channel(
        self, youtube_title: str
    ) -> OPTIONAL_STR: ...
    def truncate_to_nearest_word(self, title: str, max_length: int) -> str: ...
    def upload_video_to_youtube_with_title_thumbnail(
        self, video_file: str, youtube_title: str, youtube_description: str, thumbnail_filepath: OPTIONAL_STR
    ) -> str: ...
    def determine_thumbnail_filepath(self, video_file: str) -> OPTIONAL_STR: ...
    def determine_youtube_title(self, video_file: str) -> str: ...
    def determine_youtube_description(self, video_file: str, youtube_title: str) -> str: ...
    def process(self) -> list[dict[str, str]]: ...
