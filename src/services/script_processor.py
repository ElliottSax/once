"""
Script processing and scene generation service.

Responsible for:
- Analyzing raw text input
- Breaking scripts into logical scenes
- Estimating timing and pacing
- Identifying visual opportunities
"""

import re
from typing import List, Dict, Optional, Tuple
from loguru import logger
import spacy
from src.models.video_request import Scene, VideoScript, SceneType


class ScriptProcessor:
    """Process and structure video scripts into scenes"""

    def __init__(self):
        """Initialize the script processor with NLP models"""
        try:
            self.nlp = spacy.load("en_core_web_sm")
            logger.info("SpaCy model loaded successfully")
        except OSError:
            logger.warning("SpaCy model not found, using basic processing")
            self.nlp = None

        # Average speaking rates (words per minute)
        self.wpm_slow = 130
        self.wpm_normal = 150
        self.wpm_fast = 170

    def process_script(
        self,
        text: str,
        title: str,
        target_duration: int = 300,
        tone: str = "educational"
    ) -> VideoScript:
        """
        Process raw text into a structured video script.

        Args:
            text: Raw script text
            title: Video title
            target_duration: Target duration in seconds
            tone: Desired tone (educational, casual, professional)

        Returns:
            VideoScript with structured scenes
        """
        logger.info(f"Processing script: {title} (target: {target_duration}s)")

        # Clean and normalize text
        cleaned_text = self._clean_text(text)

        # Split into logical sections
        sections = self._split_into_sections(cleaned_text)

        # Analyze content
        key_topics = self._extract_key_topics(cleaned_text)
        complexity = self._calculate_complexity(cleaned_text)

        # Generate scenes
        scenes = self._generate_scenes(sections, title, target_duration, tone)

        # Calculate total duration
        total_duration = sum(scene.duration for scene in scenes)

        script = VideoScript(
            title=title,
            description=f"Educational video about {title}",
            scenes=scenes,
            total_duration=total_duration,
            target_audience="general",
            tone=tone,
            key_topics=key_topics,
            complexity_score=complexity
        )

        logger.info(
            f"Script processed: {len(scenes)} scenes, "
            f"{total_duration:.1f}s duration, "
            f"complexity: {complexity:.2f}"
        )

        return script

    def _clean_text(self, text: str) -> str:
        """Clean and normalize input text"""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters but keep punctuation
        text = re.sub(r'[^\w\s.,!?;:\-\'"()]', '', text)
        return text.strip()

    def _split_into_sections(self, text: str) -> List[str]:
        """Split text into logical sections based on paragraphs and sentences"""
        # Split by double newlines (paragraphs)
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]

        if not paragraphs:
            # Fallback: split by sentence groups
            sentences = re.split(r'(?<=[.!?])\s+', text)
            # Group every 2-3 sentences
            paragraphs = []
            current = []
            for i, sent in enumerate(sentences):
                current.append(sent)
                if len(current) >= 2 or i == len(sentences) - 1:
                    paragraphs.append(' '.join(current))
                    current = []

        return paragraphs

    def _extract_key_topics(self, text: str) -> List[str]:
        """Extract key topics using NLP"""
        if not self.nlp:
            # Fallback: extract capitalized words
            words = re.findall(r'\b[A-Z][a-z]+\b', text)
            return list(set(words))[:5]

        doc = self.nlp(text)

        # Extract noun chunks and named entities
        topics = set()

        # Named entities
        for ent in doc.ents:
            if ent.label_ in ['ORG', 'PRODUCT', 'EVENT', 'WORK_OF_ART', 'LAW', 'LANGUAGE']:
                topics.add(ent.text)

        # Important noun phrases
        for chunk in doc.noun_chunks:
            if len(chunk.text.split()) <= 3:  # Keep it concise
                topics.add(chunk.text)

        # Limit to top topics
        return sorted(list(topics))[:10]

    def _calculate_complexity(self, text: str) -> float:
        """
        Calculate content complexity score (0-1).

        Based on:
        - Average sentence length
        - Vocabulary diversity
        - Technical term density
        """
        if not text:
            return 0.5

        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]

        words = text.split()

        # Metrics
        avg_sentence_length = len(words) / max(len(sentences), 1)
        vocab_diversity = len(set(words)) / max(len(words), 1)

        # Normalize to 0-1 scale
        # Sentence length: 10-25 words is normal
        sentence_complexity = min((avg_sentence_length - 10) / 15, 1.0)
        sentence_complexity = max(sentence_complexity, 0.0)

        # Vocab diversity: 0.3-0.7 is normal
        vocab_complexity = (vocab_diversity - 0.3) / 0.4
        vocab_complexity = max(min(vocab_complexity, 1.0), 0.0)

        # Combine metrics
        complexity = (sentence_complexity * 0.6 + vocab_complexity * 0.4)

        return min(max(complexity, 0.1), 0.9)

    def _generate_scenes(
        self,
        sections: List[str],
        title: str,
        target_duration: int,
        tone: str
    ) -> List[Scene]:
        """Generate scenes from text sections"""
        scenes: List[Scene] = []

        # Add title scene
        title_scene = Scene(
            scene_id="scene_000_title",
            scene_type=SceneType.TITLE,
            narration_text=f"Welcome. Today we'll explore: {title}",
            visual_description=f"Title card with text: {title}",
            start_time=0.0,
            duration=4.0,
            keywords=[title],
            animation_style="fade_in"
        )
        scenes.append(title_scene)

        current_time = title_scene.duration

        # Process content sections
        for i, section in enumerate(sections):
            scene_type = self._determine_scene_type(section)
            duration = self._estimate_duration(section, tone)
            visual_desc = self._generate_visual_description(section, scene_type)
            keywords = self._extract_section_keywords(section)

            scene = Scene(
                scene_id=f"scene_{i+1:03d}",
                scene_type=scene_type,
                narration_text=section,
                visual_description=visual_desc,
                start_time=current_time,
                duration=duration,
                keywords=keywords,
                animation_style=self._suggest_animation(scene_type)
            )

            scenes.append(scene)
            current_time += duration

        # Add conclusion scene if needed
        if current_time < target_duration - 10:
            conclusion_scene = Scene(
                scene_id=f"scene_{len(scenes):03d}_conclusion",
                scene_type=SceneType.CONCLUSION,
                narration_text="Thank you for watching. If you found this helpful, please subscribe for more content.",
                visual_description="Call to action: Subscribe button with channel branding",
                start_time=current_time,
                duration=5.0,
                keywords=["conclusion", "subscribe"],
                animation_style="fade_out"
            )
            scenes.append(conclusion_scene)

        return scenes

    def _determine_scene_type(self, text: str) -> SceneType:
        """Determine the type of scene based on content"""
        text_lower = text.lower()

        # Check for comparison keywords
        if any(word in text_lower for word in ['versus', 'compared to', 'difference between', 'while']):
            return SceneType.COMPARISON

        # Check for process keywords
        if any(word in text_lower for word in ['first', 'then', 'next', 'step', 'finally']):
            return SceneType.PROCESS

        # Check for data/statistics
        if any(word in text_lower for word in ['percent', 'statistics', 'data', 'number', 'research shows']):
            return SceneType.DATA

        # Check for quotes
        if '"' in text or "'" in text:
            return SceneType.QUOTE

        # Default to concept explanation
        return SceneType.CONCEPT

    def _estimate_duration(self, text: str, tone: str) -> float:
        """Estimate scene duration based on word count and tone"""
        word_count = len(text.split())

        # Choose WPM based on tone
        wpm = {
            'educational': self.wpm_normal,
            'casual': self.wpm_fast,
            'professional': self.wpm_slow
        }.get(tone, self.wpm_normal)

        # Calculate base duration
        base_duration = (word_count / wpm) * 60

        # Add buffer for visual processing (20-30%)
        duration = base_duration * 1.25

        # Minimum 3 seconds per scene
        return max(duration, 3.0)

    def _generate_visual_description(self, text: str, scene_type: SceneType) -> str:
        """Generate description of visuals for this scene"""
        # Extract key nouns for visual generation
        if self.nlp:
            doc = self.nlp(text[:500])  # Limit to first 500 chars
            nouns = [chunk.text for chunk in doc.noun_chunks][:3]
            visual_elements = ', '.join(nouns) if nouns else 'abstract concept'
        else:
            # Fallback: use first few words
            words = text.split()[:5]
            visual_elements = ' '.join(words)

        # Template based on scene type
        templates = {
            SceneType.TITLE: "Title card with bold text and gradient background",
            SceneType.CONCEPT: f"Illustration showing {visual_elements} in modern, clean style",
            SceneType.COMPARISON: f"Split-screen comparison showing {visual_elements}",
            SceneType.PROCESS: f"Step-by-step diagram illustrating {visual_elements}",
            SceneType.DATA: f"Data visualization or infographic representing {visual_elements}",
            SceneType.QUOTE: "Quote display with elegant typography and minimal background",
            SceneType.CONCLUSION: "Closing card with channel branding and call-to-action"
        }

        return templates.get(scene_type, f"Visual representation of {visual_elements}")

    def _extract_section_keywords(self, text: str) -> List[str]:
        """Extract keywords from a text section"""
        if self.nlp:
            doc = self.nlp(text)
            # Get noun chunks
            keywords = [chunk.text.lower() for chunk in doc.noun_chunks]
            return list(set(keywords))[:5]
        else:
            # Fallback: extract longer words
            words = re.findall(r'\b\w{5,}\b', text.lower())
            return list(set(words))[:5]

    def _suggest_animation(self, scene_type: SceneType) -> str:
        """Suggest animation style based on scene type"""
        animations = {
            SceneType.TITLE: "fade_in_scale",
            SceneType.CONCEPT: "fade_slide",
            SceneType.COMPARISON: "split_reveal",
            SceneType.PROCESS: "sequence_reveal",
            SceneType.DATA: "chart_build",
            SceneType.QUOTE: "fade_in",
            SceneType.CONCLUSION: "fade_out_scale"
        }
        return animations.get(scene_type, "fade")

    def estimate_total_cost(self, script: VideoScript, settings: Dict) -> float:
        """
        Estimate total generation cost for a script.

        Args:
            script: Video script
            settings: Generation settings (quality, providers, etc.)

        Returns:
            Estimated cost in USD
        """
        # Pricing (approximate as of 2024)
        prices = {
            'narration_per_char': 0.00015,  # ElevenLabs turbo
            'dalle3_standard': 0.040,  # per image
            'dalle3_hd': 0.080,  # per image
            'sdxl': 0.002,  # per image (Replicate)
            'rendering_per_minute': 0.05  # Lambda rendering estimate
        }

        # Calculate narration cost
        total_chars = sum(len(scene.narration_text) for scene in script.scenes)
        narration_cost = total_chars * prices['narration_per_char']

        # Calculate image generation cost
        image_provider = settings.get('image_provider', 'dalle3_standard')
        num_images = len(script.scenes) - 1  # Exclude title scene
        image_cost = num_images * prices.get(image_provider, 0.04)

        # Calculate rendering cost
        duration_minutes = script.total_duration / 60
        rendering_cost = duration_minutes * prices['rendering_per_minute']

        total_cost = narration_cost + image_cost + rendering_cost

        logger.info(
            f"Cost estimate: Narration ${narration_cost:.2f}, "
            f"Images ${image_cost:.2f}, "
            f"Rendering ${rendering_cost:.2f}, "
            f"Total ${total_cost:.2f}"
        )

        return total_cost
