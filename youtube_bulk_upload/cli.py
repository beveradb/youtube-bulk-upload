#!/usr/bin/env python
import os
import argparse
import logging
import pkg_resources
from youtube_bulk_upload import YouTubeBulkUpload


def main():
    logger = logging.getLogger(__name__)
    log_handler = logging.StreamHandler()
    log_formatter = logging.Formatter(fmt="%(asctime)s.%(msecs)03d - %(levelname)s - %(module)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    log_handler.setFormatter(log_formatter)
    logger.addHandler(log_handler)

    package_version = pkg_resources.get_distribution("youtube-bulk-upload").version
    cli_description = "Upload all videos in a folder to youtube, e.g. to help re-populate an unfairly terminated channel."

    parser = argparse.ArgumentParser(
        description=cli_description, formatter_class=lambda prog: argparse.RawTextHelpFormatter(prog, max_help_position=85)
    )

    # General Options
    general_group = parser.add_argument_group("General Options")

    log_level_help = "Optional: logging level, e.g. info, debug, warning (default: %(default)s). Example: --log_level=debug"
    dry_run_help = "Optional: Enable dry run mode to print actions without executing them (default: %(default)s). Example: -n or --dry_run"
    source_directory_help = "Optional: Directory to load video files from for upload. Default: current directory"
    input_file_extensions_help = "Optional: File extensions to include in the upload. Default: %(default)s"
    noninteractive_help = (
        "Optional: Disable interactive prompt, will run fully automatically (will pring warning messages if needed). Default: %(default)s"
    )
    upload_batch_limit_help = "Optional: Limit for the number of videos to upload in a batch. Default: %(default)s"

    general_group.add_argument("-v", "--version", action="version", version=f"%(prog)s {package_version}")
    general_group.add_argument("--log_level", default="info", help=log_level_help)
    general_group.add_argument("--dry_run", "-n", action="store_true", help=dry_run_help)
    general_group.add_argument("--source_directory", default=os.getcwd(), help=source_directory_help)
    general_group.add_argument("--input_file_extensions", nargs="+", default=[".mp4", ".mov", ".avi", ".mkv", ".mpg", ".mpeg", ".wmv", ".flv", ".webm", ".m4v", ".vob"], help=input_file_extensions_help)
    general_group.add_argument("--noninteractive", default=False, action="store_true", help=noninteractive_help)
    general_group.add_argument("--upload_batch_limit", type=int, default=100, help=upload_batch_limit_help)

    # YouTube Options
    yt_group = parser.add_argument_group("YouTube Options")

    yt_client_secrets_file_help = (
        "Mandatory: File path to youtube client secrets file. Example: --yt_client_secrets_file='/path/to/client_secret.json'"
    )
    yt_category_id_help = "Optional: YouTube category ID for uploaded videos. Default: %(default)s (Music)"
    yt_keywords_help = (
        "Optional: Keywords for YouTube video, separated by spaces. Default: %(default)s. Example: --yt_keywords keyword1 keyword2 keyword3"
    )

    yt_desc_template_file_help = (
        "Optional: File path to YouTube video description template. Example: --yt_desc_template_file='/path/to/description_template.txt'"
    )
    yt_desc_replacements_help = (
        "Optional: Pairs for replacing text in the description template. Example: --yt_desc_replacements find1 replace1"
    )

    yt_title_prefix_help = "Optional: Prefix for YouTube video titles."
    yt_title_suffix_help = "Optional: Suffix for YouTube video titles."
    yt_title_replacements_help = "Optional: Pairs for replacing text in the titles. Example: --yt_title_replacements find1 replace1"

    yt_group.add_argument("--yt_client_secrets_file", default="client_secret.json", help=yt_client_secrets_file_help)
    yt_group.add_argument("--yt_category_id", default="10", help=yt_category_id_help)
    yt_group.add_argument("--yt_keywords", nargs="+", default=["music"], help=yt_keywords_help)

    yt_group.add_argument("--yt_desc_template_file", default=None, help=yt_desc_template_file_help)
    yt_group.add_argument("--yt_desc_replacements", nargs="+", action="append", help=yt_desc_replacements_help)

    yt_group.add_argument("--yt_title_prefix", default=None, help=yt_title_prefix_help)
    yt_group.add_argument("--yt_title_suffix", default=None, help=yt_title_suffix_help)
    yt_group.add_argument("--yt_title_replacements", nargs="+", action="append", help=yt_title_replacements_help)

    # Thumbnail Options
    thumbnail_group = parser.add_argument_group("Thumbnail Options")

    thumb_file_prefix_help = "Optional: Prefix for thumbnail filenames. Default: %(default)s"
    thumb_file_suffix_help = "Optional: Suffix for thumbnail filenames. Default: %(default)s"
    thumb_file_replacements_help = (
        "Optional: Pairs for replacing text in the thumbnail filenames. Example: --thumb_file_replacements find1 replace1"
    )
    thumb_file_extensions_help = "Optional: File extensions to include for thumbnails. Default: .png .jpg .jpeg"

    thumbnail_group.add_argument("--thumb_file_prefix", default=None, help=thumb_file_prefix_help)
    thumbnail_group.add_argument("--thumb_file_suffix", default=None, help=thumb_file_suffix_help)
    thumbnail_group.add_argument("--thumb_file_replacements", nargs="+", action="append", help=thumb_file_replacements_help)
    thumbnail_group.add_argument("--thumb_file_extensions", nargs="+", default=[".png", ".jpg", ".jpeg"], help=thumb_file_extensions_help)

    args = parser.parse_args()

    log_level = getattr(logging, args.log_level.upper())
    logger.setLevel(log_level)

    logger.info(f"YouTubeBulkUpload CLI beginning initialisation...")

    youtube_bulk_upload = YouTubeBulkUpload(
        logger=logger,
        dry_run=args.dry_run,
        interactive_prompt=not args.noninteractive,
        source_directory=args.source_directory,
        input_file_extensions=args.input_file_extensions,
        upload_batch_limit=args.upload_batch_limit,
        youtube_client_secrets_file=args.yt_client_secrets_file,
        youtube_category_id=args.yt_category_id,
        youtube_keywords=args.yt_keywords,
        youtube_description_template_file=args.yt_desc_template_file,
        youtube_description_replacements=args.yt_desc_replacements,
        youtube_title_prefix=args.yt_title_prefix,
        youtube_title_suffix=args.yt_title_suffix,
        youtube_title_replacements=args.yt_title_replacements,
        thumbnail_filename_prefix=args.thumb_file_prefix,
        thumbnail_filename_suffix=args.thumb_file_suffix,
        thumbnail_filename_replacements=args.thumb_file_replacements,
        thumbnail_filename_extensions=args.thumb_file_extensions,
    )

    try:
        uploaded_videos = youtube_bulk_upload.process()
    except Exception as e:
        logger.error(f"An error occurred during bulk upload, see stack trace below: {str(e)}")
        raise e

    logger.info(f"YouTube Bulk Upload processing complete! Videos uploaded to YouTube: {len(uploaded_videos)}")

    for video in uploaded_videos:
        logger.info(f"Input Filename: {video['input_filename']} - YouTube Title: {video['youtube_title']} - URL: {video['youtube_url']}")


if __name__ == "__main__":
    main()
