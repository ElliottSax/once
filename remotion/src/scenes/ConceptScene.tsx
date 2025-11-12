/**
 * Concept Scene Component
 *
 * Displays concept explanation with image and text
 */

import React from 'react';
import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  Img,
  Easing,
  staticFile,
} from 'remotion';
import { VideoScene } from '../types/VideoData';

interface ConceptSceneProps {
  scene: VideoScene;
}

export const ConceptScene: React.FC<ConceptSceneProps> = ({ scene }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const sceneFrame = frame - scene.startTime * fps;
  const sceneDuration = scene.duration * fps;

  // Image animation: slide in from left
  const imageSlide = interpolate(sceneFrame, [0, fps * 0.6], [-100, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.ease),
  });

  // Text animation: fade in slightly after image
  const textFade = interpolate(sceneFrame, [fps * 0.3, fps * 0.8], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  // Keywords animation: fade in last
  const keywordsFade = interpolate(sceneFrame, [fps * 0.6, fps * 1.2], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill
      style={{
        backgroundColor: '#1a1a2e',
        background: 'linear-gradient(180deg, #1a1a2e 0%, #16213e 100%)',
      }}
    >
      {/* Image on left side */}
      {scene.imagePath && (
        <div
          style={{
            position: 'absolute',
            left: 100,
            top: '50%',
            transform: `translate(${imageSlide}px, -50%)`,
            width: 800,
            height: 600,
            borderRadius: 20,
            overflow: 'hidden',
            boxShadow: '0 20px 60px rgba(0,0,0,0.5)',
          }}
        >
          <Img
            src={scene.imagePath}
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'cover',
            }}
          />
        </div>
      )}

      {/* Text content on right side */}
      <div
        style={{
          position: 'absolute',
          right: 100,
          top: '50%',
          transform: 'translateY(-50%)',
          width: 800,
          opacity: textFade,
        }}
      >
        <div
          style={{
            fontSize: 42,
            color: 'white',
            lineHeight: 1.6,
            fontWeight: 300,
            textShadow: '0 2px 10px rgba(0,0,0,0.3)',
          }}
        >
          {scene.narrationText}
        </div>

        {/* Keywords */}
        {scene.keywords.length > 0 && (
          <div
            style={{
              marginTop: 40,
              display: 'flex',
              gap: 15,
              flexWrap: 'wrap',
              opacity: keywordsFade,
            }}
          >
            {scene.keywords.slice(0, 5).map((keyword, i) => (
              <div
                key={i}
                style={{
                  padding: '10px 20px',
                  backgroundColor: 'rgba(102, 126, 234, 0.3)',
                  borderRadius: 25,
                  fontSize: 24,
                  color: '#a5b4fc',
                  border: '1px solid rgba(102, 126, 234, 0.5)',
                }}
              >
                {keyword}
              </div>
            ))}
          </div>
        )}
      </div>
    </AbsoluteFill>
  );
};
