"""Whisperモデルのキャッシング管理"""

import gc
import logging
from typing import Optional

from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)


class WhisperManager:
    """Whisperモデルのシングルトン管理クラス

    モデルのロード時間（10-30秒）を削減するため、
    一度ロードしたモデルをキャッシュして再利用する。
    """

    _model: Optional[WhisperModel] = None
    _device: Optional[str] = None
    _model_size: str = "large-v3"

    @classmethod
    def get_model(cls, device: str = "cuda") -> WhisperModel:
        """モデルを取得（必要に応じてロード）

        Args:
            device: 使用デバイス ("cuda" or "cpu")

        Returns:
            WhisperModel インスタンス
        """
        if cls._model is not None and cls._device == device:
            logger.debug(f"Using cached model (device={device})")
            return cls._model

        # デバイスが変わった場合は再ロード
        if cls._model is not None:
            logger.info(f"Device changed from {cls._device} to {device}, reloading model...")
            cls.unload()

        cls._load(device)
        return cls._model

    @classmethod
    def _load(cls, device: str) -> None:
        """モデルをロード"""
        logger.info(f"Loading Whisper model ({cls._model_size}) on {device}...")

        compute_type = "float16" if device == "cuda" else "int8"

        cls._model = WhisperModel(
            cls._model_size,
            device=device,
            compute_type=compute_type
        )
        cls._device = device

        logger.info(f"Model loaded successfully")

    @classmethod
    def unload(cls) -> None:
        """モデルをアンロードしてメモリ解放"""
        if cls._model is not None:
            logger.info("Unloading Whisper model...")
            del cls._model
            cls._model = None
            cls._device = None

            # ガベージコレクションを強制実行
            gc.collect()

            # CUDAメモリも解放
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    logger.debug("CUDA cache cleared")
            except ImportError:
                pass

            logger.info("Model unloaded")

    @classmethod
    def is_loaded(cls) -> bool:
        """モデルがロード済みかどうか"""
        return cls._model is not None

    @classmethod
    def current_device(cls) -> Optional[str]:
        """現在のデバイスを取得"""
        return cls._device
