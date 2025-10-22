import React, { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { useAuth } from "@/contexts/AuthContext";
import { api } from "@/lib/api";
import { AlertTriangle, Loader2 } from "lucide-react";
import { useNavigate } from "react-router-dom";

interface DeleteAccountDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export const DeleteAccountDialog: React.FC<DeleteAccountDialogProps> = ({
  open,
  onOpenChange,
}) => {
  const { signOut } = useAuth();
  const navigate = useNavigate();
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const handleDeleteAccount = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsDeleting(true);

    try {
      const response = await api.auth.deleteAccount({ password });

      if (response.success) {
        // Sign out and redirect to login page
        await signOut();
        navigate("/login", {
          replace: true,
          state: { message: "Your account has been deleted successfully." },
        });
        onOpenChange(false);
      } else {
        setError(response.message || "Failed to delete account.");
      }
    } catch (err: any) {
      setError(err.message || "Failed to delete account. Please try again.");
    } finally {
      setIsDeleting(false);
    }
  };

  const handleClose = () => {
    if (!isDeleting) {
      setPassword("");
      setError(null);
      onOpenChange(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-destructive">
            <AlertTriangle className="h-5 w-5" />
            Delete Account
          </DialogTitle>
          <DialogDescription>
            This action cannot be undone. This will permanently delete your account and
            remove all your data including:
            <ul className="mt-2 list-disc list-inside text-sm text-muted-foreground">
              <li>Your profile information</li>
              <li>All AI agents you've created</li>
              <li>All tools you've developed</li>
              <li>LLM integrations and API keys</li>
              <li>Test scenarios and execution history</li>
              <li>Game history and statistics</li>
              <li>Any remaining coins or purchases</li>
            </ul>
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleDeleteAccount} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="password">Current Password</Label>
            <Input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter your current password"
              required
              disabled={isDeleting}
            />
            <p className="text-xs text-muted-foreground">
              Please enter your password to confirm account deletion.
            </p>
          </div>

          {error && (
            <Alert variant="destructive">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <DialogFooter className="flex flex-col sm:flex-row gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={handleClose}
              disabled={isDeleting}
              className="sm:w-auto w-full"
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="destructive"
              disabled={isDeleting || !password}
              className="sm:w-auto w-full gap-2"
            >
              {isDeleting ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Deleting Account...
                </>
              ) : (
                <>
                  <AlertTriangle className="h-4 w-4" />
                  Delete Account
                </>
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};