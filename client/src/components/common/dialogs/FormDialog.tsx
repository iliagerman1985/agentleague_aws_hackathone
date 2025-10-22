import React from 'react';
import { SharedModal } from '@/components/common/SharedModal';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface FormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: string;
  children: React.ReactNode;
  onSubmit?: () => void | Promise<void>;
  onCancel?: () => void;
  submitLabel?: string;
  cancelLabel?: string;
  submitDisabled?: boolean;
  loading?: boolean;
  size?: 'sm' | 'md' | 'lg' | 'xl' | '2xl';
  className?: string;
  footerClassName?: string;
  hideFooter?: boolean;
}

/**
 * FormDialog provides a standardized dialog for forms with consistent styling and behavior
 */
export const FormDialog: React.FC<FormDialogProps> = ({
  open,
  onOpenChange,
  title,
  description,
  children,
  onSubmit,
  onCancel,
  submitLabel = 'Save',
  cancelLabel = 'Cancel',
  submitDisabled = false,
  loading = false,
  size = 'md',
  className,
  footerClassName,
  hideFooter = false
}) => {
  const handleSubmit = async () => {
    if (onSubmit) {
      await onSubmit();
    }
  };

  const handleCancel = () => {
    if (onCancel) {
      onCancel();
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
      className={cn('max-h\-[90vh] overflow-y-auto bg-card text-foreground', className)}
      contentClassName="py-4 flex-1 overflow-y-auto min-h-0"
      contentProps={{ 'data-testid': 'form-dialog' } as any}
      titleProps={{ className: 'text-xl font-semibold', 'data-testid': 'form-dialog-title' } as any}
      descriptionProps={{ className: 'text-base', 'data-testid': 'form-dialog-description' } as any}
      footer={hideFooter ? undefined : (
        <div className={cn('w-full flex items-center justify-end gap-3', footerClassName)} data-testid="form-dialog-footer">
          <Button
            variant="outline"
            onClick={handleCancel}
            disabled={loading}
            className="flex-1 sm:flex-initial min-w-[100px] bg-gradient-to-r from-gray-50 to-slate-50 border-gray-300 text-gray-700 hover:from-gray-100 hover:to-slate-100 hover:border-gray-400 hover:text-gray-800 transition-all duration-200 shadow-sm"
            data-testid="form-dialog-cancel"
          >
            {cancelLabel}
          </Button>
          {onSubmit && (
            <Button
              onClick={handleSubmit}
              disabled={submitDisabled || loading}
              className="flex-1 sm:flex-initial min-w-[100px] bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-600 hover:to-teal-600 text-white shadow-md transition-all duration-200"
              data-testid="form-dialog-submit"
            >
              {loading ? 'Saving...' : submitLabel}
            </Button>
          )}
        </div>
      )}
    >
      <div data-testid="form-dialog-content">{children}</div>
    </SharedModal>
  );
};

export default FormDialog;
