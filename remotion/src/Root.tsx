/**
 * Remotion Root Component
 *
 * Defines all available video compositions.
 */

import React from 'react';
import { Composition } from 'remotion';
import { ExplainerVideo } from './compositions/ExplainerVideo';

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="ExplainerVideo"
        component={ExplainerVideo}
        durationInFrames={300 * 30} // 5 minutes at 30fps
        fps={30}
        width={1920}
        height={1080}
        defaultProps={{
          title: 'Sample Explainer Video',
          scenes: [],
        }}
      />
    </>
  );
};
