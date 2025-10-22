declare module '@/components/Particles' {
  const Particles: React.FC<{
    particleColors?: string[];
    particleCount?: number;
    particleSpread?: number;
    speed?: number;
    particleBaseSize?: number;
    moveParticlesOnHover?: boolean;
    particleHoverFactor?: number;
    alphaParticles?: boolean;
    sizeRandomness?: number;
    cameraDistance?: number;
    disableRotation?: boolean;
  }>;
  export default Particles;
}