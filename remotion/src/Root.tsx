/**
 * Remotion Root Component
 *
 * Defines all available video compositions.
 */

import React from 'react';
import { Composition } from 'remotion';
import { ExplainerVideo, ExplainerVideoProps } from './compositions/ExplainerVideo';
import { FullVideo, FullVideoProps } from './compositions/FullVideo';
import { VideoData } from './types/VideoData';

export const RemotionRoot: React.FC = () => {
  // Legacy simple composition
  const defaultProps: ExplainerVideoProps = {
    title: 'Sample Explainer Video',
    scenes: [],
  };

  // Default video data for FullVideo composition
  const defaultVideoData: VideoData = {
    title: 'Sample Video',
    description: 'Video description',
    scenes: [],
    totalDuration: 60,
    quality: 'standard',
    metadata: {
      requestId: 'sample',
      createdAt: new Date().toISOString(),
      targetAudience: 'general',
      tone: 'educational',
    },
  };

  return (
    <>
      {/* Legacy composition */}
      <Composition
        id="ExplainerVideo"
        component={ExplainerVideo}
        durationInFrames={300 * 30}
        fps={30}
        width={1920}
        height={1080}
        defaultProps={defaultProps}
      />

      {/* Main production composition */}
      <Composition
        id="FullVideo"
        component={FullVideo}
        // Duration will be overridden by CLI with --props
        durationInFrames={300 * 30}
        fps={30}
        width={1920}
        height={1080}
        defaultProps={{ videoData: defaultVideoData }}
      />
    </>
  );
};
