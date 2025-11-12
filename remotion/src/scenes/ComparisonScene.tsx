/**
 * Comparison Scene Component
 *
 * Side-by-side comparison display
 */

import React from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate, Img } from 'remotion';
import { VideoScene } from '../types/VideoData';

interface ComparisonSceneProps {
  scene: VideoScene;
}

export const ComparisonScene: React.FC<ComparisonSceneProps> = ({ scene }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const sceneFrame = frame - scene.startTime * fps;

  // Split reveal animation
  const leftReveal = interpolate(sceneFrame, [0, fps * 0.5], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  const rightReveal = interpolate(sceneFrame, [fps * 0.3, fps * 0.8], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  const textFade = interpolate(sceneFrame, [fps * 0.6, fps * 1.2], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  // Extract comparison keywords (assume first two are the items being compared)
  const leftItem = scene.keywords[0] || 'Option A';
  const rightItem = scene.keywords[1] || 'Option B';

  return (
    <AbsoluteFill style={{ backgroundColor: '#0f172a' }}>
      {/* Left side */}
      <div
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          width: '50%',
          height: '100%',
          opacity: leftReveal,
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          padding: 60,
        }}
      >
        <div
          style={{
            fontSize: 56,
            fontWeight: 'bold',
            color: 'white',
            marginBottom: 30,
            textTransform: 'uppercase',
            letterSpacing: 2,
          }}
        >
          {leftItem}
        </div>
        {scene.imagePath && (
          <div
            style={{
              width: 400,
              height: 300,
              borderRadius: 15,
              overflow: 'hidden',
              boxShadow: '0 10px 40px rgba(0,0,0,0.4)',
            }}
          >
            <Img
              src={scene.imagePath}
              style={{ width: '100%', height: '100%', objectFit: 'cover' }}
            />
          </div>
        )}
      </div>

      {/* Right side */}
      <div
        style={{
          position: 'absolute',
          right: 0,
          top: 0,
          width: '50%',
          height: '100%',
          opacity: rightReveal,
          background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          padding: 60,
        }}
      >
        <div
          style={{
            fontSize: 56,
            fontWeight: 'bold',
            color: 'white',
            marginBottom: 30,
            textTransform: 'uppercase',
            letterSpacing: 2,
          }}
        >
          {rightItem}
        </div>
        {scene.imagePath && (
          <div
            style={{
              width: 400,
              height: 300,
              borderRadius: 15,
              overflow: 'hidden',
              boxShadow: '0 10px 40px rgba(0,0,0,0.4)',
            }}
          >
            <Img
              src={scene.imagePath}
              style={{ width: '100%', height: '100%', objectFit: 'cover' }}
            />
          </div>
        )}
      </div>

      {/* Divider */}
      <div
        style={{
          position: 'absolute',
          left: '50%',
          top: '10%',
          transform: 'translateX(-50%)',
          width: 4,
          height: '80%',
          background: 'white',
          boxShadow: '0 0 20px rgba(255,255,255,0.5)',
        }}
      />

      {/* VS badge */}
      <div
        style={{
          position: 'absolute',
          left: '50%',
          top: '50%',
          transform: 'translate(-50%, -50%)',
          width: 120,
          height: 120,
          borderRadius: '50%',
          background: 'white',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: 48,
          fontWeight: 'bold',
          color: '#0f172a',
          boxShadow: '0 10px 40px rgba(0,0,0,0.3)',
          opacity: textFade,
        }}
      >
        VS
      </div>

      {/* Narration text at bottom */}
      <div
        style={{
          position: 'absolute',
          bottom: 80,
          left: '50%',
          transform: 'translateX(-50%)',
          width: '80%',
          textAlign: 'center',
          fontSize: 32,
          color: 'white',
          opacity: textFade,
          padding: '30px 40px',
          backgroundColor: 'rgba(0,0,0,0.6)',
          borderRadius: 15,
          backdropFilter: 'blur(10px)',
        }}
      >
        {scene.narrationText}
      </div>
    </AbsoluteFill>
  );
};
