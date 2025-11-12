/**
 * Title Scene Component
 *
 * Displays the video title with animated entrance
 */

import React from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate, Easing } from 'remotion';
import { VideoScene } from '../types/VideoData';

interface TitleSceneProps {
  scene: VideoScene;
}

export const TitleScene: React.FC<TitleSceneProps> = ({ scene }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Calculate scene-relative frame (0 at scene start)
  const sceneFrame = frame - (scene.startTime * fps);
  const sceneDuration = scene.duration * fps;

  // Animation: Fade in and scale
  const fadeIn = interpolate(sceneFrame, [0, fps * 0.5], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.ease),
  });

  const scale = interpolate(sceneFrame, [0, fps * 0.5], [0.8, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.ease),
  });

  // Fade out near end
  const fadeOut = interpolate(
    sceneFrame,
    [sceneDuration - fps * 0.3, sceneDuration],
    [1, 0],
    {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
    }
  );

  const opacity = Math.min(fadeIn, fadeOut);

  return (
    <AbsoluteFill
      style={{
        backgroundColor: '#0f0f23',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        justifyContent: 'center',
        alignItems: 'center',
      }}
    >
      <div
        style={{
          opacity,
          transform: `scale(${scale})`,
          textAlign: 'center',
          padding: '0 80px',
        }}
      >
        <h1
          style={{
            fontSize: 96,
            fontWeight: 'bold',
            color: 'white',
            margin: 0,
            textShadow: '0 4px 20px rgba(0,0,0,0.3)',
            lineHeight: 1.2,
          }}
        >
          {scene.narrationText || 'Video Title'}
        </h1>

        {scene.keywords.length > 0 && (
          <div
            style={{
              marginTop: 40,
              fontSize: 32,
              color: 'rgba(255,255,255,0.8)',
              fontWeight: 300,
            }}
          >
            {scene.keywords.slice(0, 3).join(' • ')}
          </div>
        )}
      </div>
    </AbsoluteFill>
  );
};
