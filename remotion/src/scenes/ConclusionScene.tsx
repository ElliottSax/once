/**
 * Conclusion Scene Component
 *
 * Call-to-action and closing
 */

import React from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate, Easing } from 'remotion';
import { VideoScene } from '../types/VideoData';

interface ConclusionSceneProps {
  scene: VideoScene;
}

export const ConclusionScene: React.FC<ConclusionSceneProps> = ({ scene }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const sceneFrame = frame - scene.startTime * fps;

  // Fade in animation
  const fadeIn = interpolate(sceneFrame, [0, fps * 0.5], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.ease),
  });

  // Scale animation for CTA button
  const buttonScale = interpolate(
    sceneFrame,
    [fps * 0.8, fps * 1.2, fps * 1.6, fps * 2.0],
    [0, 1.1, 0.95, 1],
    {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
      easing: Easing.inOut(Easing.ease),
    }
  );

  return (
    <AbsoluteFill
      style={{
        backgroundColor: '#0f0f23',
        background: 'linear-gradient(135deg, #1e3a8a 0%, #312e81 100%)',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        padding: 80,
      }}
    >
      <div style={{ opacity: fadeIn, textAlign: 'center' }}>
        {/* Thank you message */}
        <div
          style={{
            fontSize: 64,
            fontWeight: 'bold',
            color: 'white',
            marginBottom: 40,
            textShadow: '0 4px 20px rgba(0,0,0,0.3)',
          }}
        >
          Thank You for Watching!
        </div>

        {/* Narration text */}
        <div
          style={{
            fontSize: 36,
            color: 'rgba(255,255,255,0.9)',
            marginBottom: 60,
            maxWidth: 1200,
            lineHeight: 1.5,
          }}
        >
          {scene.narrationText}
        </div>

        {/* CTA buttons */}
        <div
          style={{
            display: 'flex',
            gap: 40,
            justifyContent: 'center',
            transform: `scale(${buttonScale})`,
          }}
        >
          {/* Subscribe button */}
          <div
            style={{
              padding: '25px 60px',
              backgroundColor: '#ef4444',
              borderRadius: 50,
              fontSize: 36,
              fontWeight: 'bold',
              color: 'white',
              boxShadow: '0 10px 40px rgba(239, 68, 68, 0.4)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 15,
            }}
          >
            <span>👍</span>
            <span>SUBSCRIBE</span>
          </div>

          {/* Like button */}
          <div
            style={{
              padding: '25px 60px',
              backgroundColor: 'rgba(255,255,255,0.1)',
              border: '3px solid white',
              borderRadius: 50,
              fontSize: 36,
              fontWeight: 'bold',
              color: 'white',
              boxShadow: '0 10px 40px rgba(255,255,255,0.1)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 15,
            }}
          >
            <span>❤️</span>
            <span>LIKE</span>
          </div>
        </div>

        {/* Keywords / Social */}
        {scene.keywords.length > 0 && (
          <div
            style={{
              marginTop: 60,
              fontSize: 24,
              color: 'rgba(255,255,255,0.6)',
            }}
          >
            {scene.keywords.join(' • ')}
          </div>
        )}
      </div>
    </AbsoluteFill>
  );
};
