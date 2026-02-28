#!/usr/bin/env python3
"""
Download InsightFace models offline before running the pipeline.

Usage:
    python tools/download_models.py [--model buffalo_l]

This ensures the models are cached locally and avoids download issues on first run.
"""

import argparse
import sys
import os
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

VALID_MODELS = ["buffalo_l", "buffalo_s", "buffalo_sc"]


def download_models(model_name: str = "buffalo_l"):
    """Download an InsightFace model pack."""
    try:
        import insightface
        from insightface.app import FaceAnalysis
        
        logger.info("Downloading model: %s", model_name)
        logger.info("This may take 1-5 minutes depending on connection speed")
        
        # Create FaceAnalysis instance - this triggers model download
        app = FaceAnalysis(name=model_name, providers=["CPUExecutionProvider"])
        
        # Prepare the model (required before use)
        app.prepare(ctx_id=-1, det_size=(640, 640))
        
        logger.info("Models downloaded and cached successfully!")
        logger.info("Location: ~/.insightface/models/%s/", model_name)
        return True
        
    except Exception as e:
        logger.error("Model download failed: %s", e)
        logger.error("Please try again or manually download from:")
        logger.error("https://github.com/deepinsight/insightface/tree/master/model_zoo")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download InsightFace models")
    parser.add_argument(
        "--model", default="buffalo_l", choices=VALID_MODELS,
        help="Model pack to download (default: buffalo_l, use buffalo_s for RPi)"
    )
    args = parser.parse_args()
    success = download_models(args.model)
    sys.exit(0 if success else 1)
