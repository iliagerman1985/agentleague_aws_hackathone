import React from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { cn } from "@/lib/utils";

export interface SharedModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
  size?: "sm" | "md" | "lg" | "xl" | "2xl" | "full";
  className?: string; // extra classes for DialogContent wrapper
  contentClassName?: string; // inner content container customization
  titleProps?: React.ComponentPropsWithoutRef<typeof DialogTitle> | Record<string, any>;
  descriptionProps?: React.ComponentPropsWithoutRef<typeof DialogDescription> | Record<string, any>;
  contentProps?: React.ComponentPropsWithoutRef<typeof DialogContent> | Record<string, any>;
}

const sizeClasses: Record<NonNullable<SharedModalProps["size"]>, string> = {
  sm: "sm:max-w-md",
  md: "sm:max-w-lg",
  lg: "sm:max-w-2xl",
  xl: "sm:max-w-4xl",
  "2xl": "sm:max-w-6xl",
  full: "w-[96vw] max-w-[96vw] h-[96vh]",
};

export const SharedModal: React.FC<SharedModalProps> = ({
  open,
  onOpenChange,
  title,
  description,
  children,
  footer,
  size = "lg",
  className,
  contentClassName,
  titleProps,
  descriptionProps,
  contentProps,
}) => {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className={cn(sizeClasses[size], className)} {...(contentProps as any)}>
        <DialogHeader>
          <DialogTitle {...(titleProps as any)}>{title}</DialogTitle>
          {description && <DialogDescription {...(descriptionProps as any)}>{description}</DialogDescription>}
        </DialogHeader>
        <div className={cn("mt-2", contentClassName)}>{children}</div>
        {footer ? <DialogFooter>{footer}</DialogFooter> : null}
      </DialogContent>
    </Dialog>
  );
};

export default SharedModal;

