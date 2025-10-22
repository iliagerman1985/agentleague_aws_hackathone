declare module '@/components/Galaxy' {
  import React from 'react';

  interface GalaxyProps {
    focal?: [number, number];
    rotation?: [number, number];
    starSpeed?: number;
    density?: number;
    hueShift?: number;
    disableAnimation?: boolean;
    speed?: number;
    mouseInteraction?: boolean;
    glowIntensity?: number;
    saturation?: number;
    mouseRepulsion?: boolean;
    repulsionStrength?: number;
    twinkleIntensity?: number;
    rotationSpeed?: number;
    autoCenterRepulsion?: number;
    transparent?: boolean;
  }

  const Galaxy: React.FC<GalaxyProps>;
  export default Galaxy;
}

