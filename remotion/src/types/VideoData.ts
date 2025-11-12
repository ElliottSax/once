/**
 * Type definitions for video data passed from Python to Remotion
 */

export interface VideoScene {
  id: string;
  type: 'title' | 'concept' | 'comparison' | 'process' | 'data' | 'quote' | 'conclusion';
  narrationText: string;
  visualDescription: string;
  startTime: number;
  duration: number;
  audioPath: string | null;
  imagePath: string | null;
  animationStyle: string;
  keywords: string[];
}

export interface VideoMetadata {
  requestId: string;
  createdAt: string;
  targetAudience: string;
  tone: string;
}

export interface VideoData {
  title: string;
  description: string;
  scenes: VideoScene[];
  totalDuration: number;
  quality: 'draft' | 'standard' | 'premium';
  metadata: VideoMetadata;
}
