declare module '@/components/Ballpit' {
  import React from 'react';

  interface BallpitProps {
    count?: number;
    gravity?: number;
    friction?: number;
    wallBounce?: number;
    followCursor?: boolean;
    colors?: number[];
  }

  const Ballpit: React.FC<BallpitProps>;
  export default Ballpit;
}

