import React from "react";
import { SharedModal } from "@/components/common/SharedModal";
import { DialogFooter } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";

export interface ConfirmDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title?: string;
  description?: string;
  confirmText?: string;
  cancelText?: string;
  onConfirm?: () => void;
  variant?: "default" | "destructive" | "outline" | "secondary" | "ghost" | "link" | "cta";
}

export const ConfirmDialog: React.FC<ConfirmDialogProps> = ({
  open,
  onOpenChange,
  title = "Confirm Action",
  description = "Are you sure you want to proceed?",
  confirmText = "Confirm",
  cancelText = "Cancel",
  onConfirm,
  variant = "cta",
}) => {
  return (
    <SharedModal
      open={open}
      onOpenChange={onOpenChange}
      title={title}
      description={description}
      size="sm"
      contentProps={{ 'data-testid': 'confirm-dialog' } as any}
      titleProps={{ 'data-testid': 'confirm-dialog-title' } as any}
      descriptionProps={{ 'data-testid': 'confirm-dialog-description' } as any}
    >
      <DialogFooter className="border-t-0">
        <Button variant="outline" onClick={() => onOpenChange(false)} data-testid="confirm-dialog-cancel">{cancelText}</Button>
        <Button variant={variant} onClick={() => { onConfirm?.(); onOpenChange(false); }} data-testid="confirm-dialog-confirm">{confirmText}</Button>
      </DialogFooter>
    </SharedModal>
  );
};

