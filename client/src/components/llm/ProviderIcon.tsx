import React from "react";
import { LLMProvider } from "@/lib/api";

interface ProviderIconProps {
  provider: LLMProvider | string;
  size?: number; // px
  className?: string;
  alt?: string;
}

const providerToIconSrc = (provider: string): string => {
  switch (provider) {
    case "openai":
      return "/icons/providers/openai.svg";
    case "anthropic":
      return "/icons/providers/anthropic.svg";
    case "google":
      return "/icons/providers/gemini.svg";
    case "aws_bedrock":
      return "/icons/providers/amazon-bedrock.svg";
    default:
      return "/icon.svg"; // fallback app icon
  }
};

export const ProviderIcon: React.FC<ProviderIconProps> = ({ provider, size = 16, className = "", alt }) => {
  const p = typeof provider === "string" ? provider : String(provider);
  const src = providerToIconSrc(p);
  const computedAlt = alt ?? `${p} logo`;
  return (
    <img
      src={src}
      alt={computedAlt}
      width={size}
      height={size}
      className={className}
      style={{ width: `${size}px`, height: `${size}px` }}
    />
  );
};

export default ProviderIcon;

