#!/usr/bin/env python
import argparse
import logging
import pkg_resources
import os
import sys
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
        description=cli_description, formatter_class=lambda prog: argparse.RawTextHelpFormatter(prog, max_help_position=54)
    )

    # General Options
    general_group = parser.add_argument_group("General Options")

    log_level_help = "Optional: logging level, e.g. info, debug, warning (default: %(default)s). Example: --log_level=debug"
    dry_run_help = "Optional: Enable dry run mode to print actions without executing them (default: %(default)s). Example: -n or --dry_run"
    input_file_extensions_help = "Optional: File extensions to include in the upload. Default: %(default)s"
    interactive_prompt_help = "Optional: Enable interactive prompt mode. Default: %(default)s"
    upload_batch_limit_help = "Optional: Limit for the number of videos to upload in a batch. Default: %(default)s"

    general_group.add_argument("-v", "--version", action="version", version=f"%(prog)s {package_version}")
    general_group.add_argument("--log_level", default="info", help=log_level_help)
    general_group.add_argument("--dry_run", "-n", action="store_true", help=dry_run_help)
    general_group.add_argument("--input_file_extensions", nargs="+", default=[".mp4", ".mov"], help=input_file_extensions_help)
    general_group.add_argument("--interactive_prompt", action="store_true", default=True, help=interactive_prompt_help)
    general_group.add_argument("--upload_batch_limit", type=int, default=100, help=upload_batch_limit_help)

    # YouTube Options
    youtube_group = parser.add_argument_group("YouTube Options")

    youtube_client_secrets_file_help = "Optional: File path to youtube client secrets file. Example: --youtube_client_secrets_file='/path/to/client_secret_1234567890_apps.googleusercontent.com.json'"
    youtube_category_id_help = "Optional: YouTube category ID for uploaded videos. Default: %(default)s (Music)"
    youtube_keywords_help = "Optional: Keywords for YouTube video, separated by spaces. Default: %(default)s. Example: --youtube_keywords keyword1 keyword2 keyword3"

    youtube_description_template_file_help = "Optional: File path to YouTube video description template. Example: --youtube_description_template_file='/path/to/description_template.txt'"
    youtube_description_replacements_help = "Optional: Pairs for replacing text in the YouTube video description template. Example: --youtube_description_replacements placeholder1 replacement1 placeholder2 replacement2"

    youtube_title_prefix_help = "Optional: Prefix for YouTube video titles."
    youtube_title_suffix_help = "Optional: Suffix for YouTube video titles."
    youtube_title_replacements_help = "Optional: Pairs for replacing text in the YouTube video titles. Example: --youtube_title_replacements placeholder1 replacement1 placeholder2 replacement2"

    youtube_group.add_argument("--youtube_client_secrets_file", default=None, help=youtube_client_secrets_file_help)
    youtube_group.add_argument("--youtube_category_id", default="10", help=youtube_category_id_help)
    youtube_group.add_argument("--youtube_keywords", nargs="+", default=["music"], help=youtube_keywords_help)

    youtube_group.add_argument("--youtube_description_template_file", default=None, help=youtube_description_template_file_help)
    youtube_group.add_argument("--youtube_description_replacements", nargs="+", action="append", help=youtube_description_replacements_help)

    youtube_group.add_argument("--youtube_title_prefix", default=None, help=youtube_title_prefix_help)
    youtube_group.add_argument("--youtube_title_suffix", default=None, help=youtube_title_suffix_help)
    youtube_group.add_argument("--youtube_title_replacements", nargs="+", action="append", help=youtube_title_replacements_help)

    # Thumbnail Options
    thumbnail_group = parser.add_argument_group("Thumbnail Options")

    thumbnail_filename_prefix_help = "Optional: Prefix for thumbnail filenames. Default: %(default)s"
    thumbnail_filename_suffix_help = "Optional: Suffix for thumbnail filenames. Default: %(default)s"
    thumbnail_filename_replacements_help = "Optional: Pairs for replacing text in the thumbnail filenames. Example: --thumbnail_filename_replacements placeholder1 replacement1 placeholder2 replacement2"
    thumbnail_filename_extensions_help = "Optional: File extensions to include for thumbnails. Default: .png .jpg .jpeg"

    thumbnail_group.add_argument("--thumbnail_filename_prefix", default=None, help=thumbnail_filename_prefix_help)
    thumbnail_group.add_argument("--thumbnail_filename_suffix", default=None, help=thumbnail_filename_suffix_help)
    thumbnail_group.add_argument("--thumbnail_filename_replacements", nargs="+", action="append", help=thumbnail_filename_replacements_help)
    thumbnail_group.add_argument(
        "--thumbnail_filename_extensions", nargs="+", default=[".png", ".jpg", ".jpeg"], help=thumbnail_filename_extensions_help
    )

    args = parser.parse_args()

    log_level = getattr(logging, args.log_level.upper())
    logger.setLevel(log_level)

    logger.info(f"YouTubeBulkUpload CLI beginning initialisation...")

    youtube_bulk_upload = YouTubeBulkUpload(
        log_formatter=log_formatter,
        log_level=log_level,
        dry_run=args.dry_run,
        interactive_prompt=args.interactive_prompt,
        input_file_extensions=args.input_file_extensions,
        upload_batch_limit=args.upload_batch_limit,
        youtube_client_secrets_file=args.youtube_client_secrets_file,
        youtube_category_id=args.youtube_category_id,
        youtube_keywords=args.youtube_keywords,
        youtube_description_template_file=args.youtube_description_template_file,
        youtube_description_replacements=args.youtube_description_replacements,
        youtube_title_prefix=args.youtube_title_prefix,
        youtube_title_suffix=args.youtube_title_suffix,
        youtube_title_replacements=args.youtube_title_replacements,
        thumbnail_filename_prefix=args.thumbnail_filename_prefix,
        thumbnail_filename_suffix=args.thumbnail_filename_suffix,
        thumbnail_filename_replacements=args.thumbnail_filename_replacements,
        thumbnail_filename_extensions=args.thumbnail_filename_extensions,
    )

    try:
        uploaded_videos = youtube_bulk_upload.process()
    except Exception as e:
        logger.error(f"An error occurred during bulk upload, see stack trace below: {str(e)}")
        raise e

    logger.info(f"YouTube Bulk Upload processing complete! Videos uploaded to YouTube:")
    logger.info(f"")
    for video in uploaded_videos:
        logger.info(f"Input Filename: {video['input_filename']} - YouTube Title: {video['youtube_title']} - URL: {video['youtube_url']}")


if __name__ == "__main__":
    main()
