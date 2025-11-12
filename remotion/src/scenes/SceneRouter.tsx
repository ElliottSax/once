/**
 * Scene Router Component
 *
 * Routes to appropriate scene component based on scene type
 */

import React from 'react';
import { VideoScene } from '../types/VideoData';
import { TitleScene } from './TitleScene';
import { ConceptScene } from './ConceptScene';
import { ComparisonScene } from './ComparisonScene';
import { ConclusionScene } from './ConclusionScene';

interface SceneRouterProps {
  scene: VideoScene;
}

export const SceneRouter: React.FC<SceneRouterProps> = ({ scene }) => {
  switch (scene.type) {
    case 'title':
      return <TitleScene scene={scene} />;

    case 'concept':
      return <ConceptScene scene={scene} />;

    case 'comparison':
      return <ComparisonScene scene={scene} />;

    case 'conclusion':
      return <ConclusionScene scene={scene} />;

    case 'process':
      // Use ConceptScene for now, can be specialized later
      return <ConceptScene scene={scene} />;

    case 'data':
      // Use ConceptScene for now, can add data viz later
      return <ConceptScene scene={scene} />;

    case 'quote':
      // Use ConceptScene for now, can add quote styling later
      return <ConceptScene scene={scene} />;

    default:
      return <ConceptScene scene={scene} />;
  }
};
