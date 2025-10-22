import React, { useId, useRef } from "react";
import { Camera, Trash2 } from "lucide-react";
import { Avatar, type AvatarProps } from "./Avatar";
import { AvatarCropDialog, type CropData } from "./AvatarCropDialog";
import { cn } from "@/lib/utils";

export interface AvatarUploadProps extends Omit<AvatarProps, "src"> {
  /** Current avatar URL */
  currentAvatar?: string | null;
  /** Upload handler function - now receives file and optional crop data */
  onUpload: (file: File, cropData?: CropData) => Promise<void>;
  /** Remove handler function */
  onRemove?: () => Promise<void>;
  /** Whether upload is in progress */
  uploading?: boolean;
  /** Whether the component is disabled */
  disabled?: boolean;
  /** Acceptable file types */
  accept?: string;
  /** Maximum file size in bytes */
  maxSize?: number;
  /** Whether remove action can be invoked */
  canRemove?: boolean;
  /** Optional helper text to render beneath controls */
  helperText?: React.ReactNode;
  /** Whether to show the helper text block under the avatar */
  showHelperText?: boolean;
  /** Whether to show the camera button in the overlay */
  showCameraButton?: boolean;
  /** Whether to enable crop functionality */
  enableCrop?: boolean;
}

const DEFAULT_MAX_SIZE = 5 * 1024 * 1024; // 5MB
const DEFAULT_ACCEPT = "image/jpeg,image/jpg,image/png,image/webp,image/gif";

/**
 * AvatarUpload component for uploading and managing avatar images.
 * Combines Avatar display with upload/remove functionality.
 */
export const AvatarUpload: React.FC<AvatarUploadProps> = ({
  currentAvatar,
  onUpload,
  onRemove,
  uploading = false,
  disabled = false,
  accept = DEFAULT_ACCEPT,
  maxSize = DEFAULT_MAX_SIZE,
  size = "xl",
  fallback,
  className,
  showBorder = true,
  type = "default",
  canRemove = true,
  helperText,
  showHelperText = true,
  showCameraButton = true,
  enableCrop = true,
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const inputId = useId();
  const [mobileMenuOpen, setMobileMenuOpen] = React.useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const [cropDialogOpen, setCropDialogOpen] = React.useState(false);
  const [selectedFile, setSelectedFile] = React.useState<File | null>(null);

  // Close the mobile submenu on outside tap
  React.useEffect(() => {
    if (!mobileMenuOpen) return;
    const onPointerDown = (e: PointerEvent) => {
      if (!containerRef.current) return;
      if (!containerRef.current.contains(e.target as Node)) {
        setMobileMenuOpen(false);
      }
    };
    window.addEventListener("pointerdown", onPointerDown, true);
    return () => window.removeEventListener("pointerdown", onPointerDown, true);
  }, [mobileMenuOpen]);

  // Helper to detect mobile viewport
  const isMobileViewport = () => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") return false;
    return window.matchMedia('(max-width: 767px)').matches;
  };

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Validate file size
    if (file.size > maxSize) {
      alert(`File too large. Maximum size is ${maxSize / (1024 * 1024)}MB`);
      return;
    }

    // Validate file type
    if (!accept.split(",").some(type => file.type.includes(type.replace("image/", "")))) {
      alert(`Invalid file type. Accepted types: ${accept.replace(/image\//g, "").split(",").join(", ")}`);
      return;
    }

    // If crop is enabled, show crop dialog
    if (enableCrop) {
      setSelectedFile(file);
      setCropDialogOpen(true);
    } else {
      // Upload directly without cropping
      onUpload(file);
    }

    // Reset file input
    event.target.value = "";
  };

  const handleCropComplete = async (cropData: CropData) => {
    if (!selectedFile) return;

    setCropDialogOpen(false);
    await onUpload(selectedFile, cropData);
    setSelectedFile(null);
  };

  const handleCropCancel = () => {
    setCropDialogOpen(false);
    setSelectedFile(null);
  };

  const triggerUpload = () => {
    if (!disabled && !uploading) {
      fileInputRef.current?.click();
    }
  };

  const handleKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === "Escape") {
      setMobileMenuOpen(false);
      return;
    }
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      if (isMobileViewport()) {
        setMobileMenuOpen((v) => !v);
      } else {
        triggerUpload();
      }
    }
  };

  const handleRemove = async (event?: React.MouseEvent | React.TouchEvent) => {
    event?.preventDefault();
    event?.stopPropagation();
    if (!disabled && onRemove) {
      await onRemove();
    }
  };

  const shouldShowRemove = Boolean(onRemove && canRemove);
  const helperContent = helperText ?? (
    <>
      <span>Max file size: {maxSize / (1024 * 1024)}MB</span>
      <br />
      <span>Accepted formats: {accept.replace(/image\//g, "").split(",").join(", ").toUpperCase()}</span>
    </>
  );

  return (
    <div className={cn("flex flex-col items-center gap-3", className)}>
      <div className="relative inline-flex items-center gap-3 md:flex-col md:gap-4">
        <div ref={containerRef} className="relative inline-flex rounded-full group">
          <div
            role="button"
            tabIndex={disabled ? -1 : 0}
            onClick={(event) => {
              event.preventDefault();
              if (isMobileViewport()) {
                setMobileMenuOpen((v) => !v);
              } else {
                triggerUpload();
              }
            }}
            onKeyDown={disabled ? undefined : handleKeyDown}
            className={cn(
              "relative rounded-full outline-none focus-visible:ring-4 focus-visible:ring-brand-teal/40 focus-visible:ring-offset-2",
              (disabled || uploading) && "cursor-not-allowed opacity-60",
            )}
            aria-label="Change avatar"
          >
            <Avatar
              src={currentAvatar}
              fallback={fallback}
              size={size}
              showBorder={showBorder}
              type={type}
              className="transition-opacity"
            />

            {uploading && (
              <div className="pointer-events-none absolute inset-0 flex items-center justify-center rounded-full bg-black/40">
                <div className="h-7 w-7 animate-spin rounded-full border-2 border-white/40 border-t-white" />
              </div>
            )}
          </div>

          {/* Overlay controls container */}
          <div className="absolute inset-0 rounded-full pointer-events-none group-hover:pointer-events-auto">
            {/* Desktop: show trash (and optional camera) on hover */}
            <div className="flex items-center justify-center h-full w-full rounded-full bg-black/45 opacity-0 transition-opacity group-hover:opacity-100">
              <div className="flex items-center gap-3">
                {showCameraButton && (
                  <button
                    type="button"
                    className="pointer-events-auto inline-flex h-11 w-11 items-center justify-center rounded-full bg-white/95 text-brand-teal shadow-md ring-1 ring-border transition hover:scale-105"
                    onClick={(event) => {
                      event.preventDefault();
                      event.stopPropagation();
                      triggerUpload();
                    }}
                    disabled={disabled || uploading}
                    aria-label="Upload new avatar"
                  >
                    <Camera className="h-5 w-5" />
                  </button>
                )}
                {shouldShowRemove && (
                  <button
                    type="button"
                    className="pointer-events-auto inline-flex h-11 w-11 items-center justify-center rounded-full bg-white/95 text-destructive shadow-md ring-1 ring-border transition hover:scale-105"
                    onClick={handleRemove}
                    disabled={disabled || uploading}
                    aria-label="Remove avatar"
                  >
                    <Trash2 className="h-5 w-5" />
                  </button>
                )}
              </div>
            </div>

            {/* Mobile radial menu (shows on tap) */}
            {shouldShowRemove && (
              <div
                className={cn(
                  "md:hidden absolute inset-0 flex items-end justify-center pb-1",
                  mobileMenuOpen ? "pointer-events-auto" : "pointer-events-none"
                )}
                onClick={(e) => { e.stopPropagation(); }}
              >
                {mobileMenuOpen && (
                  <div className="flex items-center gap-2 bg-black/55 rounded-full px-2 py-1 ring-1 ring-white/20 backdrop-blur-sm">
                    <button
                      type="button"
                      className="inline-flex h-9 w-9 items-center justify-center rounded-full bg-white/95 text-brand-teal shadow ring-1 ring-border"
                      onClick={(e) => { e.preventDefault(); e.stopPropagation(); triggerUpload(); setMobileMenuOpen(false); }}
                      aria-label="Upload new avatar"
                    >
                      <Camera className="h-4 w-4" />
                    </button>
                    <button
                      type="button"
                      className="inline-flex h-9 w-9 items-center justify-center rounded-full bg-white/95 text-destructive shadow ring-1 ring-border"
                      onClick={(e) => { e.preventDefault(); e.stopPropagation(); handleRemove(e); setMobileMenuOpen(false); }}
                      aria-label="Remove avatar"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      <input
        ref={fileInputRef}
        type="file"
        accept={accept}
        onChange={handleFileSelect}
        className="hidden absolute opacity-0 pointer-events-none"
        style={{ display: 'none' }}
        aria-hidden
        disabled={disabled || uploading}
        id={inputId}
      />

      {showHelperText && (
        <div className="text-center text-xs text-muted-foreground leading-relaxed">
          {helperContent}
        </div>
      )}

      {/* Crop Dialog */}
      <AvatarCropDialog
        open={cropDialogOpen}
        onOpenChange={setCropDialogOpen}
        imageFile={selectedFile}
        onCropComplete={handleCropComplete}
        onCancel={handleCropCancel}
      />
    </div>
  );
};

export default AvatarUpload;