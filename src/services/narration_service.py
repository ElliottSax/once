"""
Narration generation service using ElevenLabs and other TTS providers.

Handles:
- Text-to-speech generation
- Audio post-processing
- Timing synchronization with Whisper
- Audio quality optimization
"""

import asyncio
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from loguru import logger
import aiohttp
import soundfile as sf
import numpy as np
from pydub import AudioSegment
import pyloudnorm as pyln

from config.settings import get_settings


class NarrationService:
    """Generate and process narration audio"""

    def __init__(self):
        """Initialize narration service"""
        self.settings = get_settings()
        self.session: Optional[aiohttp.ClientSession] = None

        # Audio processing settings
        self.target_loudness = -16.0  # LUFS (standard for YouTube)
        self.sample_rate = 44100
        self.channels = 1  # Mono

    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    async def generate_narration(
        self,
        text: str,
        output_path: Path,
        voice_id: Optional[str] = None,
        voice_settings: Optional[Dict] = None
    ) -> Tuple[Path, float]:
        """
        Generate narration audio from text.

        Args:
            text: Text to convert to speech
            output_path: Where to save the audio file
            voice_id: ElevenLabs voice ID (optional)
            voice_settings: Custom voice settings (optional)

        Returns:
            Tuple of (audio_path, duration_seconds)
        """
        logger.info(f"Generating narration: {len(text)} characters")

        # Select provider based on settings
        provider = self.settings.default_voice_provider

        if provider.startswith('elevenlabs'):
            audio_path = await self._generate_elevenlabs(
                text, output_path, voice_id, voice_settings
            )
        else:
            raise ValueError(f"Unsupported voice provider: {provider}")

        # Post-process audio
        audio_path = await self._post_process_audio(audio_path)

        # Get duration
        duration = self._get_audio_duration(audio_path)

        logger.info(f"Narration generated: {duration:.2f}s, saved to {audio_path}")

        return audio_path, duration

    async def generate_batch(
        self,
        texts: List[str],
        output_dir: Path,
        voice_id: Optional[str] = None
    ) -> List[Tuple[Path, float]]:
        """
        Generate multiple narrations concurrently.

        Args:
            texts: List of texts to convert
            output_dir: Directory to save audio files
            voice_id: ElevenLabs voice ID (optional)

        Returns:
            List of (audio_path, duration) tuples
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        tasks = []
        for i, text in enumerate(texts):
            output_path = output_dir / f"narration_{i:03d}.mp3"
            task = self.generate_narration(text, output_path, voice_id)
            tasks.append(task)

        # Limit concurrent requests
        max_concurrent = self.settings.max_concurrent_generations
        results = []

        for i in range(0, len(tasks), max_concurrent):
            batch = tasks[i:i + max_concurrent]
            batch_results = await asyncio.gather(*batch, return_exceptions=True)

            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"Narration generation failed: {result}")
                    results.append((None, 0.0))
                else:
                    results.append(result)

        return results

    async def _generate_elevenlabs(
        self,
        text: str,
        output_path: Path,
        voice_id: Optional[str],
        voice_settings: Optional[Dict]
    ) -> Path:
        """Generate audio using ElevenLabs API"""
        if not self.session:
            self.session = aiohttp.ClientSession()

        # Default voice (can be configured)
        if not voice_id:
            voice_id = "21m00Tcm4TlvDq8ikWAM"  # Rachel voice

        # Default settings
        if not voice_settings:
            voice_settings = {
                "stability": 0.5,
                "similarity_boost": 0.75,
                "style": 0.0,
                "use_speaker_boost": True
            }

        # Choose model based on provider setting
        provider = self.settings.default_voice_provider
        if provider == "elevenlabs_turbo":
            model_id = "eleven_turbo_v2"
        elif provider == "elevenlabs_premium":
            model_id = "eleven_multilingual_v2"
        else:
            model_id = "eleven_monolingual_v1"

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.settings.elevenlabs_api_key
        }

        payload = {
            "text": text,
            "model_id": model_id,
            "voice_settings": voice_settings
        }

        try:
            async with self.session.post(url, json=payload, headers=headers) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"ElevenLabs API error: {response.status} - {error_text}")

                # Save audio data
                audio_data = await response.read()
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(audio_data)

                logger.debug(f"Audio saved: {len(audio_data)} bytes")

        except Exception as e:
            logger.error(f"ElevenLabs generation failed: {e}")
            raise

        return output_path

    async def _post_process_audio(self, audio_path: Path) -> Path:
        """
        Post-process audio for consistent quality.

        - Normalize loudness
        - Remove silence
        - Apply compression
        """
        try:
            # Load audio
            audio = AudioSegment.from_file(str(audio_path))

            # Convert to mono if needed
            if audio.channels > 1:
                audio = audio.set_channels(1)

            # Normalize sample rate
            if audio.frame_rate != self.sample_rate:
                audio = audio.set_frame_rate(self.sample_rate)

            # Export to numpy for loudness normalization
            samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
            samples = samples / np.iinfo(audio.array_type).max

            # Loudness normalization
            meter = pyln.Meter(self.sample_rate)
            loudness = meter.integrated_loudness(samples)

            if not np.isnan(loudness) and not np.isinf(loudness):
                normalized = pyln.normalize.loudness(samples, loudness, self.target_loudness)
                # Clip to prevent distortion
                normalized = np.clip(normalized, -1.0, 1.0)

                # Convert back to AudioSegment
                normalized_int = (normalized * np.iinfo(audio.array_type).max).astype(audio.array_type)
                audio = AudioSegment(
                    data=normalized_int.tobytes(),
                    sample_width=audio.sample_width,
                    frame_rate=self.sample_rate,
                    channels=1
                )

            # Remove leading/trailing silence
            audio = self._strip_silence(audio, silence_thresh=-40)

            # Save processed audio
            audio.export(str(audio_path), format="mp3", bitrate="192k")

            logger.debug(f"Audio post-processed: {audio_path}")

        except Exception as e:
            logger.warning(f"Audio post-processing failed: {e}, using original")

        return audio_path

    def _strip_silence(
        self,
        audio: AudioSegment,
        silence_thresh: int = -40,
        chunk_size: int = 10
    ) -> AudioSegment:
        """Remove silence from beginning and end of audio"""
        # Detect non-silent chunks
        non_silent_ranges = self._detect_nonsilent(
            audio,
            min_silence_len=500,
            silence_thresh=silence_thresh,
            seek_step=chunk_size
        )

        if not non_silent_ranges:
            return audio

        # Get first and last non-silent positions
        start = max(0, non_silent_ranges[0][0] - 100)  # Keep 100ms buffer
        end = min(len(audio), non_silent_ranges[-1][1] + 100)

        return audio[start:end]

    def _detect_nonsilent(
        self,
        audio: AudioSegment,
        min_silence_len: int = 1000,
        silence_thresh: int = -40,
        seek_step: int = 1
    ) -> List[Tuple[int, int]]:
        """Detect non-silent chunks in audio"""
        # Simple implementation
        silent = []
        for i in range(0, len(audio), seek_step):
            chunk = audio[i:i + min_silence_len]
            if chunk.dBFS < silence_thresh:
                silent.append(i)

        # Find continuous ranges
        ranges = []
        if not silent:
            return [(0, len(audio))]

        start = 0
        for pos in silent:
            if pos - start > min_silence_len:
                ranges.append((start, pos))
            start = pos + min_silence_len

        if start < len(audio):
            ranges.append((start, len(audio)))

        return ranges if ranges else [(0, len(audio))]

    def _get_audio_duration(self, audio_path: Path) -> float:
        """Get duration of audio file in seconds"""
        try:
            audio = AudioSegment.from_file(str(audio_path))
            return len(audio) / 1000.0  # Convert ms to seconds
        except Exception as e:
            logger.error(f"Failed to get audio duration: {e}")
            return 0.0

    def estimate_cost(self, text: str, provider: str = "elevenlabs_turbo") -> float:
        """
        Estimate cost for generating narration.

        Args:
            text: Text to synthesize
            provider: Voice provider

        Returns:
            Estimated cost in USD
        """
        char_count = len(text)

        # ElevenLabs pricing (approximate)
        prices_per_char = {
            "elevenlabs_turbo": 0.00015,
            "elevenlabs_standard": 0.00018,
            "elevenlabs_premium": 0.00024
        }

        price = prices_per_char.get(provider, 0.00018)
        return char_count * price


# Convenience function for synchronous usage
def generate_narration_sync(
    text: str,
    output_path: Path,
    voice_id: Optional[str] = None
) -> Tuple[Path, float]:
    """Synchronous wrapper for narration generation"""
    async def _generate():
        async with NarrationService() as service:
            return await service.generate_narration(text, output_path, voice_id)

    return asyncio.run(_generate())
