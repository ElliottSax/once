/**
 * Main Explainer Video Composition
 *
 * This is the primary video composition that assembles all scenes
 * with synchronized audio and animations.
 */

import React from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from 'remotion';

export interface ExplainerVideoProps {
  title?: string;
  scenes?: any[]; // TODO: Define proper Scene type
}

export const ExplainerVideo: React.FC<ExplainerVideoProps> = ({
  title = 'Explainer Video',
  scenes = [],
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  return (
    <AbsoluteFill
      style={{
        backgroundColor: '#1a1a1a',
        justifyContent: 'center',
        alignItems: 'center',
      }}
    >
      <div
        style={{
          color: 'white',
          fontSize: 72,
          fontFamily: 'Arial, sans-serif',
          textAlign: 'center',
          padding: 40,
        }}
      >
        {title}
        <div style={{ fontSize: 24, marginTop: 20, opacity: 0.7 }}>
          Frame: {frame} / {durationInFrames}
        </div>
        <div style={{ fontSize: 20, marginTop: 10, opacity: 0.5 }}>
          🚧 Under Construction - Scene rendering coming soon
        </div>
      </div>
    </AbsoluteFill>
  );
};
