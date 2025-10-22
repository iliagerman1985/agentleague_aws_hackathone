import React from "react";
import { useAppearance, COLOR_SCHEMES, type ColorSchemeOption } from "@/contexts/AppearanceContext";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface ColorSchemePreviewProps {
  scheme: ColorSchemeOption;
  isSelected: boolean;
  onClick: () => void;
}

const ColorSchemePreview: React.FC<ColorSchemePreviewProps> = ({ scheme, isSelected, onClick }) => {
  return (
    <Card
      className={cn(
        "relative cursor-pointer transition-all duration-200",
        "border-2 p-3",
        isSelected
          ? "border-primary shadow-md ring-2 ring-primary/20"
          : "border-border hover:border-primary/50"
      )}
      onClick={onClick}
    >
      <div className="space-y-3">
        {/* Color Preview */}
        <div className="flex space-x-2">
          <div
            className="w-8 h-8 rounded-lg shadow-sm border border-white/20"
            style={{ backgroundColor: scheme.primary }}
            title={`Primary: ${scheme.primary}`}
          />
          <div
            className="w-8 h-8 rounded-lg shadow-sm border border-white/20"
            style={{ backgroundColor: scheme.accent }}
            title={`Accent: ${scheme.accent}`}
          />
          <div
            className="w-8 h-8 rounded-lg shadow-sm border border-white/20"
            style={{ backgroundColor: scheme.preview.background }}
            title={`Background: ${scheme.preview.background}`}
          />
        </div>

        {/* Mini UI Preview */}
        <div 
          className="rounded-md p-2 space-y-1"
          style={{ backgroundColor: scheme.preview.background }}
        >
          <div
            className="h-2 w-3/4 rounded-sm"
            style={{ backgroundColor: scheme.primary }}
          />
          <div
            className="h-1.5 w-1/2 rounded-sm"
            style={{ backgroundColor: scheme.accent }}
          />
          <div className="h-1 w-2/3 rounded-sm bg-white/20" />
        </div>

        {/* Labels */}
        <div className="space-y-1">
          <h4 className="font-medium text-sm text-foreground">{scheme.name}</h4>
          <p className="text-xs text-muted-foreground">{scheme.description}</p>
        </div>

        {/* Selected Indicator */}
        {isSelected && (
          <div className="absolute top-2 right-2">
            <div className="w-3 h-3 rounded-full bg-primary border-2 border-background shadow-sm" />
          </div>
        )}
      </div>
    </Card>
  );
};

export const ColorSchemeSelector: React.FC = () => {
  const { colorScheme, setColorScheme } = useAppearance();

  return (
    <div className="space-y-4">
      <div>
        <label className="text-sm font-medium text-foreground">Color Scheme</label>
        <p className="text-sm text-muted-foreground">Choose your preferred color theme</p>
      </div>
      
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
        {COLOR_SCHEMES.map((scheme) => (
          <ColorSchemePreview
            key={scheme.id}
            scheme={scheme}
            isSelected={colorScheme === scheme.id}
            onClick={() => setColorScheme(scheme.id)}
          />
        ))}
      </div>
    </div>
  );
};