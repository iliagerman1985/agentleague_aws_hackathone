import React from 'react';
import { SharedModal } from '@/components/common/SharedModal';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface ContentDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: string;
  children: React.ReactNode;
  onClose?: () => void;
  closeLabel?: string;
  size?: 'sm' | 'md' | 'lg' | 'xl' | '2xl';
  className?: string;
  footerClassName?: string;
  hideFooter?: boolean;
  actions?: React.ReactNode;
}

/**
 * ContentDialog provides a standardized dialog for displaying content with consistent styling
 */
export const ContentDialog: React.FC<ContentDialogProps> = ({
  open,
  onOpenChange,
  title,
  description,
  children,
  onClose,
  closeLabel = 'Close',
  size = 'md',
  className,
  footerClassName,
  hideFooter = false,
  actions
}) => {


  const handleClose = () => {
    if (onClose) {
      onClose();
    } else {
      onOpenChange(false);
    }
  };

  return (
    <SharedModal
      open={open}
      onOpenChange={onOpenChange}
      title={title}
      description={description}
      size={size}
      className={cn('max-h\-[90vh] overflow-y-auto', className)}
      contentClassName="py-4"
      footer={hideFooter ? undefined : (
        <div className={cn('w-full flex items-center justify-end gap-2', footerClassName)}>
          {actions || (
            <Button variant="outline" onClick={handleClose}>{closeLabel}</Button>
          )}
        </div>
      )}
    >
      {children}
    </SharedModal>
  );
};

export default ContentDialog;
