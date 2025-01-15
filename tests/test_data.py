import os
from unittest.mock import Mock
from logging import Logger, StreamHandler, Formatter

# sample messages
sample_message = "sample message"
sample_prompt = "sample prompt"
sample_exit_message = "sample exit message"


# fake file or folder paths
fake_secrets_file_path = os.path.join("fake", "path.json")
invalid_file_path = os.path.join("fake", "file", ".txt")
folder_path = os.path.join("fake", "folder", "path")
thumbnail_filepath = os.path.join("thumbnail", "png")

# video details
valid_video_file_path = os.path.join("fake", "file", ".mp4")
sample_video_file = "video.mp4"
sample_video_title = "Sample Video Title"
sample_video_id = "video123"
sample_description = "Sample Description"
sample_chunk_size = 5242880

# Mocks
mock_formatter = Mock(spec=Formatter)
mock_handler = Mock(spec=StreamHandler, formatter=mock_formatter)
mock_logger = Mock(spec=Logger, handlers=[mock_handler])

# YouTube mocks
mock_channel_id = "UC1234567890"
mock_channel_response = {"items": [{"id": mock_channel_id}]}
mock_video_response = {
    "items": [
        {
            "snippet": {"title": sample_video_title},
            "id": {"videoId": sample_video_id},
        }
    ]
}
mock_empty_response: dict[str, list[str]] = {"items": []}
mock_mediaFileUpload_response = {"id": sample_video_id}
