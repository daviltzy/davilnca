from flask import Blueprint, request, jsonify, after_this_request
import uuid
import threading
import logging
from services.transcription import process_transcription
from services.authentication import authenticate
from services.webhook import send_webhook

transcribe_bp = Blueprint('transcribe', __name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@transcribe_bp.route('/transcribe', methods=['POST'])
@authenticate
def transcribe():
    data = request.json
    media_url = data.get('media_url')
    output = data.get('output', 'transcript').lower()
    webhook_url = data.get('webhook_url')
    id = data.get('id')

    logger.info(f"Received transcription request: media_url={media_url}, output={output}, webhook_url={webhook_url}, id={id}")

    if not media_url:
        logger.error("Missing media_url parameter in request")
        return jsonify({"error": "Missing media_url parameter"}), 400

    # Check if either webhook_url or id is missing and return the appropriate message
    if webhook_url and not id:
        logger.warning("id is missing when webhook_url is provided")
        return jsonify({"message": "It appears that the id is missing. Please review your API call and try again."}), 500
    elif id and not webhook_url:
        logger.warning("webhook_url is missing when id is provided")
        return jsonify({"message": "It appears that the webhook_url is missing. Please review your API call and try again."}), 500

    job_id = str(uuid.uuid4())
    logger.info(f"Generated job_id: {job_id}")

    def process_and_notify(media_url, output, webhook_url, id, job_id):
        try:
            logger.info(f"Job {job_id}: Starting transcription process for {media_url}")
            result = process_transcription(media_url, output)
            logger.info(f"Job {job_id}: Transcription process completed successfully")

            if webhook_url:
                logger.info(f"Job {job_id}: Sending success webhook to {webhook_url}")
                send_webhook(webhook_url, {
                    "endpoint": "/transcribe",
                    "id": id,
                    "response": result,
                    "code": 200,
                    "message": "success"
                })
        except Exception as e:
            logger.error(f"Job {job_id}: Error during transcription - {e}")
            if webhook_url:
                logger.info(f"Job {job_id}: Sending failure webhook to {webhook_url}")
                send_webhook(webhook_url, {
                    "endpoint": "/transcribe",
                    "id": id,
                    "response": None,
                    "code": 500,
                    "message": str(e)
                })

    @after_this_request
    def start_background_processing(response):
        logger.info(f"Job {job_id}: Starting background processing thread")
        thread = threading.Thread(target=process_and_notify, args=(media_url, output, webhook_url, id, job_id))
        thread.start()
        return response

    # If webhook_url and id are provided, return 202 Accepted
    if webhook_url and id:
        logger.info(f"Job {job_id}: Returning 202 Accepted response and processing in background")
        return jsonify({"message": "processing"}), 202
    else:
        try:
            logger.info(f"Job {job_id}: No webhook provided, processing synchronously")
            result = process_transcription(media_url, output)
            logger.info(f"Job {job_id}: Returning transcription result")
            return jsonify({"response": result}), 200
        except Exception as e:
            logger.error(f"Job {job_id}: Error during synchronous transcription - {e}")
            return jsonify({"message": str(e)}), 500
