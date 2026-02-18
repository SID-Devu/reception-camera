#!/usr/bin/env python3
"""
Download InsightFace models offline before running the pipeline.

Usage:
    python tools/download_models.py

This ensures the models are cached locally and avoids download issues on first run.
"""

import sys
import os
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def download_models():
    """Download InsightFace buffalo_l model pack."""
    try:
        import insightface
        from insightface.app import FaceAnalysis
        
        logger.info("Starting model download...")
        logger.info("This may take 1-5 minutes depending on connection speed")
        
        # Create FaceAnalysis instance - this triggers model download
        app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
        
        # Prepare the model (required before use)
        app.prepare(ctx_id=-1, det_size=(640, 640))
        
        logger.info("✅ Models downloaded and cached successfully!")
        logger.info("Location: ~/.insightface/models/buffalo_l/")
        return True
        
    except Exception as e:
        logger.error(f"❌ Model download failed: {e}")
        logger.error("Please try again or manually download from:")
        logger.error("https://github.com/deepinsight/insightface/tree/master/model_zoo")
        return False


if __name__ == "__main__":
    success = download_models()
    sys.exit(0 if success else 1)
