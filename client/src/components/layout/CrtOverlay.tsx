import React from "react";

export const CrtOverlay: React.FC = () => (
  <div className="pointer-events-none fixed inset-0 z-0 mix-blend-soft-light opacity-[.06] dark:opacity-[.12]">
    {/* Scanlines */}
    <div className="absolute inset-0 bg-[repeating-linear-gradient(0deg,rgba(255,255,255,.08)_0px,rgba(255,255,255,.08)_1px,transparent_2px,transparent_3px)]" />
    {/* Vignette */}
    <div className="absolute inset-0 bg-[radial-gradient(60%_80%_at_50%_50%,rgba(0,0,0,.35),transparent_60%)]" />
  </div>
);

export default CrtOverlay;

