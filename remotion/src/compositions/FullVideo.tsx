/**
 * Full Video Composition
 *
 * Renders complete video with all scenes and audio
 */

import React from 'react';
import { AbsoluteFill, Audio, Sequence, useVideoConfig, staticFile } from 'remotion';
import { VideoData, VideoScene } from '../types/VideoData';
import { SceneRouter } from '../scenes/SceneRouter';

export interface FullVideoProps {
  videoData: VideoData;
}

export const FullVideo: React.FC<FullVideoProps> = ({ videoData }) => {
  const { fps } = useVideoConfig();

  return (
    <AbsoluteFill style={{ backgroundColor: '#000' }}>
      {/* Render each scene */}
      {videoData.scenes.map((scene, index) => {
        const startFrame = Math.floor(scene.startTime * fps);
        const durationFrames = Math.floor(scene.duration * fps);

        return (
          <Sequence
            key={scene.id}
            from={startFrame}
            durationInFrames={durationFrames}
          >
            {/* Visual content */}
            <SceneRouter scene={scene} />

            {/* Audio for this scene */}
            {scene.audioPath && (
              <Audio
                src={scene.audioPath}
                startFrom={0}
                endAt={durationFrames}
              />
            )}
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};
