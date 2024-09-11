import os
import whisper
import srt
from datetime import timedelta
from services.file_management import download_file
import logging

# Set up logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Set the default local storage directory
STORAGE_PATH = "/tmp/"

def process_transcription(media_url, output_type):
    """Transcribe media and return the transcript or SRT file."""
    logger.info(f"Starting transcription for media URL: {media_url} with output type: {output_type}")
    input_filename = download_file(media_url, os.path.join(STORAGE_PATH, 'input_media'))
    logger.info(f"Downloaded media to local file: {input_filename}")

    try:
        model = whisper.load_model("base")
        logger.info("Loaded Whisper model")

        result = model.transcribe(input_filename)
        logger.info("Transcription completed")

        if output_type == 'transcript':
            output = result['text']
            logger.info("Generated transcript output")
        elif output_type == 'srt':
            srt_subtitles = []
            for i, segment in enumerate(result['segments'], start=1):
                start = timedelta(seconds=segment['start'])
                end = timedelta(seconds=segment['end'])
                text = segment['text'].strip()
                srt_subtitles.append(srt.Subtitle(i, start, end, text))
            output = srt.compose(srt_subtitles)
            logger.info("Generated SRT output")
        else:
            raise ValueError("Invalid output type. Must be 'transcript' or 'srt'.")

        os.remove(input_filename)
        logger.info(f"Removed local file: {input_filename}")
        logger.info(f"Transcription successful, output type: {output_type}")
        return output
    except Exception as e:
        logger.error(f"Transcription failed: {str(e)}")
        raise