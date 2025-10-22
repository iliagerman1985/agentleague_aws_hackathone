import React, { useRef, useEffect } from 'react';
import { useTheme } from '@/hooks/useTheme';

// Utility to parse RGB values from CSS variable strings
const cssColorToRGB = (cssVar: string): [number, number, number] => {
  // This is a fallback for server-side rendering or if CSS variables are not yet available.
  if (typeof window === 'undefined') {
    return [234, 88, 12]; // Default orange
  }
  const temp = document.createElement('div');
  temp.style.color = cssVar;
  document.body.appendChild(temp);
  const rgb = getComputedStyle(temp).color;
  document.body.removeChild(temp);
  const m = rgb.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/);
  if (!m) return [234, 88, 12]; // Default orange
  return [parseInt(m[1], 10), parseInt(m[2], 10), parseInt(m[3], 10)];
};

interface Particle {
  x: number;
  y: number;
  radius: number;
  color: [number, number, number];
  alpha: number;
  vx: number;
  vy: number;
  life: number;
  maxLife: number;
  waveOffset: number;
}

export const AppBackground: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const { animation } = useTheme();
  const particlesRef = useRef<Particle[]>([]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);

    const colors: [number, number, number][] = [
      cssColorToRGB('var(--brand-teal)'),
      cssColorToRGB('var(--brand-orange)'),
      cssColorToRGB('var(--brand-mint)'),
      cssColorToRGB('var(--brand-purple)'),
      cssColorToRGB('var(--brand-cyan)'),
      cssColorToRGB('var(--brand-amber)'),
    ];

    const createParticle = (
      x: number,
      y: number,
      radius: number,
      color: [number, number, number],
      vx: number,
      vy: number,
      life: number,
      waveOffset: number
    ): Particle => ({
      x, y, radius, color, alpha: 1, vx, vy, life, maxLife: life, waveOffset
    });

    const MAX_PARTICLES = 600;

    // Spawn a single stream of particles
    const spawnStream = () => {
      const streamDirection = Math.floor(Math.random() * 4);
      const color = colors[Math.floor(Math.random() * colors.length)];
      const numParticles = 20;
      const life = 300; // Life in frames (approx 5 seconds at 60fps)

      const startY = Math.random() * canvas.height / dpr;
      const startX = Math.random() * canvas.width / dpr;

      for (let i = 0; i < numParticles; i++) {
        const radius = 10 + i * 1.5;
        const waveOffset = Math.random() * Math.PI * 2;
        let p: Particle;

        switch (streamDirection) {
          case 0: // Left to Right
            p = createParticle(-radius, startY, radius, color, 2 + i * 0.1, 0, life - i * 5, waveOffset);
            p.vy = 0.5;
            break;
          case 1: // Top to Bottom
            p = createParticle(startX, -radius, radius, color, 0, 2 + i * 0.1, life - i * 5, waveOffset);
            p.vx = 0.5;
            break;
          case 2: // Right to Left
            p = createParticle(canvas.width / dpr + radius, startY, radius, color, -(2 + i * 0.1), 0, life - i * 5, waveOffset);
            p.vy = -0.5;
            break;
          default: // Bottom to Top
            p = createParticle(startX, canvas.height / dpr + radius, radius, color, 0, -(2 + i * 0.1), life - i * 5, waveOffset);
            p.vx = -0.5;
            break;
        }
        particlesRef.current.push(p);
      }

      // Safety cap to avoid runaway accumulation
      if (particlesRef.current.length > MAX_PARTICLES) {
        particlesRef.current.splice(0, particlesRef.current.length - MAX_PARTICLES);
      }
    };

    // Random interval helper (ms)
    const randomIntervalMs = () => (
      animation.timing.backgroundSmokeInterval[0] +
      Math.random() * (animation.timing.backgroundSmokeInterval[1] - animation.timing.backgroundSmokeInterval[0])
    );

    let nextSpawnIn = randomIntervalMs();
    let lastTime = performance.now();
    let timeSinceSpawn = 0;

    let animationFrameId: number;
    const animate = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      particlesRef.current = particlesRef.current.filter(p => p.life > 0);

      particlesRef.current.forEach(p => {
        p.life -= 1;
        p.alpha = (p.life / p.maxLife) * 0.7; // Fade out
        p.x += p.vx;
        p.y += p.vy;
        if (p.vx !== 0) {
          p.y += Math.sin(p.waveOffset + p.life * 0.05) * 1.5;
        } else {
          p.x += Math.sin(p.waveOffset + p.life * 0.05) * 1.5;
        }
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2, false);
        ctx.fillStyle = `rgba(${p.color[0]}, ${p.color[1]}, ${p.color[2]}, ${p.alpha})`;
        ctx.shadowColor = `rgba(${p.color[0]}, ${p.color[1]}, ${p.color[2]}, ${p.alpha * 0.7})`;
        ctx.shadowBlur = 20;
        ctx.fill();
      });
      ctx.shadowBlur = 0;

      // Time-based spawn using rAF (no setTimeout)
      const now = performance.now();
      const delta = now - lastTime;
      lastTime = now;
      if (!document.hidden) {
        timeSinceSpawn += delta;
        if (timeSinceSpawn >= nextSpawnIn) {
          spawnStream();
          timeSinceSpawn = 0;
          nextSpawnIn = randomIntervalMs();
        }
      } else {
        // If hidden, keep timers fresh so no backlog accumulates
        timeSinceSpawn = 0;
        nextSpawnIn = randomIntervalMs();
      }

      animationFrameId = requestAnimationFrame(animate);
    };

    // Start immediately with one stream so users see something at first paint
    spawnStream();
    animate();

    return () => {
      cancelAnimationFrame(animationFrameId);
    };
  }, [animation.timing.backgroundSmokeInterval]);

  return (
    <canvas
      ref={canvasRef}
      className="pointer-events-none fixed inset-0 z-0 h-full w-full"
    />
  );
};

export default AppBackground;
