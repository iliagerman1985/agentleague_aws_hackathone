import React, { useRef, useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import { ZoomIn, ZoomOut } from "lucide-react";
import { cn } from "@/lib/utils";

export interface CropData {
  x: number;
  y: number;
  size: number;
  scale: number;
}

interface AvatarCropDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  imageFile: File | null;
  onCropComplete: (cropData: CropData) => void;
  onCancel: () => void;
}

export const AvatarCropDialog: React.FC<AvatarCropDialogProps> = ({
  open,
  onOpenChange,
  imageFile,
  onCropComplete,
  onCancel,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [image, setImage] = useState<HTMLImageElement | null>(null);
  const [scale, setScale] = useState(1);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [containerSize, setContainerSize] = useState({ width: 0, height: 0 });

  // Load image when file changes
  useEffect(() => {
    if (!imageFile) {
      setImage(null);
      return;
    }

    const url = URL.createObjectURL(imageFile);

    const img = new Image();
    img.onload = () => {
      setImage(img);
      // Center the image initially
      if (containerRef.current) {
        const container = containerRef.current;
        const containerWidth = container.clientWidth;
        const containerHeight = container.clientHeight;
        
        // Calculate initial scale to fit the image
        const scaleX = containerWidth / img.width;
        const scaleY = containerHeight / img.height;
        const initialScale = Math.max(scaleX, scaleY, 0.5);
        
        setScale(initialScale);
        setPosition({ x: 0, y: 0 });
        setContainerSize({ width: containerWidth, height: containerHeight });
      }
    };
    img.src = url;

    return () => {
      URL.revokeObjectURL(url);
    };
  }, [imageFile]);

  // Draw canvas
  useEffect(() => {
    if (!canvasRef.current || !image || !containerSize.width) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // Set canvas size to match container
    canvas.width = containerSize.width;
    canvas.height = containerSize.height;

    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Calculate scaled image dimensions
    const scaledWidth = image.width * scale;
    const scaledHeight = image.height * scale;

    // Calculate image position (centered + user offset)
    const imgX = (canvas.width - scaledWidth) / 2 + position.x;
    const imgY = (canvas.height - scaledHeight) / 2 + position.y;

    // Draw image
    ctx.drawImage(image, imgX, imgY, scaledWidth, scaledHeight);

    // Draw overlay (darken everything outside the circle)
    ctx.save();
    ctx.fillStyle = "rgba(0, 0, 0, 0.5)";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Cut out the circle
    const circleRadius = Math.min(canvas.width, canvas.height) * 0.35;
    const circleCenterX = canvas.width / 2;
    const circleCenterY = canvas.height / 2;

    ctx.globalCompositeOperation = "destination-out";
    ctx.beginPath();
    ctx.arc(circleCenterX, circleCenterY, circleRadius, 0, Math.PI * 2);
    ctx.fill();

    // Draw circle border
    ctx.globalCompositeOperation = "source-over";
    ctx.strokeStyle = "#0891B2";
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.arc(circleCenterX, circleCenterY, circleRadius, 0, Math.PI * 2);
    ctx.stroke();

    ctx.restore();
  }, [image, scale, position, containerSize]);

  // Handle container resize
  useEffect(() => {
    if (!containerRef.current) return;

    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setContainerSize({
          width: entry.contentRect.width,
          height: entry.contentRect.height,
        });
      }
    });

    resizeObserver.observe(containerRef.current);
    return () => resizeObserver.disconnect();
  }, []);

  const handleMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true);
    setDragStart({ x: e.clientX - position.x, y: e.clientY - position.y });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging) return;
    setPosition({
      x: e.clientX - dragStart.x,
      y: e.clientY - dragStart.y,
    });
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const handleTouchStart = (e: React.TouchEvent) => {
    if (e.touches.length === 1) {
      setIsDragging(true);
      setDragStart({
        x: e.touches[0].clientX - position.x,
        y: e.touches[0].clientY - position.y,
      });
    }
  };

  const handleTouchMove = (e: React.TouchEvent) => {
    if (!isDragging || e.touches.length !== 1) return;
    setPosition({
      x: e.touches[0].clientX - dragStart.x,
      y: e.touches[0].clientY - dragStart.y,
    });
  };

  const handleTouchEnd = () => {
    setIsDragging(false);
  };

  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? -0.1 : 0.1;
    setScale((prev) => Math.max(0.5, Math.min(5, prev + delta)));
  };

  const handleCrop = () => {
    if (!image || !containerSize.width) return;

    const canvas = canvasRef.current;
    if (!canvas) return;

    // Calculate crop area in original image coordinates
    const circleRadius = Math.min(canvas.width, canvas.height) * 0.35;
    const circleCenterX = canvas.width / 2;
    const circleCenterY = canvas.height / 2;

    const scaledWidth = image.width * scale;
    const scaledHeight = image.height * scale;
    const imgX = (canvas.width - scaledWidth) / 2 + position.x;
    const imgY = (canvas.height - scaledHeight) / 2 + position.y;

    // Convert circle center to image coordinates
    const cropCenterX = (circleCenterX - imgX) / scale;
    const cropCenterY = (circleCenterY - imgY) / scale;
    const cropRadius = circleRadius / scale;

    // Calculate crop box (top-left corner and size)
    const cropData: CropData = {
      x: Math.max(0, cropCenterX - cropRadius),
      y: Math.max(0, cropCenterY - cropRadius),
      size: cropRadius * 2,
      scale: scale,
    };

    onCropComplete(cropData);
  };

  const handleCancel = () => {
    setScale(1);
    setPosition({ x: 0, y: 0 });
    onCancel();
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Crop Avatar</DialogTitle>
          <DialogDescription>
            Drag to reposition and use the slider to zoom. The circular area will be your avatar.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Canvas container */}
          <div
            ref={containerRef}
            className={cn(
              "relative w-full bg-gray-100 dark:bg-gray-900 rounded-lg overflow-hidden",
              "aspect-square max-h-[400px]",
              isDragging ? "cursor-grabbing" : "cursor-grab"
            )}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
            onTouchStart={handleTouchStart}
            onTouchMove={handleTouchMove}
            onTouchEnd={handleTouchEnd}
            onWheel={handleWheel}
          >
            <canvas
              ref={canvasRef}
              className="w-full h-full"
              style={{ touchAction: "none" }}
            />
          </div>

          {/* Zoom controls */}
          <div className="flex items-center gap-3">
            <ZoomOut className="h-4 w-4 text-muted-foreground" />
            <Slider
              value={[scale]}
              onValueChange={(values) => setScale(values[0])}
              min={0.5}
              max={5}
              step={0.1}
              className="flex-1"
            />
            <ZoomIn className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm text-muted-foreground min-w-[3rem] text-right">
              {Math.round(scale * 100)}%
            </span>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleCancel}>
            Cancel
          </Button>
          <Button onClick={handleCrop} disabled={!image}>
            Apply Crop
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

