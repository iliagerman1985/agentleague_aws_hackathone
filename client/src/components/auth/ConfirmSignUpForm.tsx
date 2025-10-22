import React, { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Logo } from '@/components/ui/logo';
import { api } from '@/lib/api';

export const ConfirmSignUpForm: React.FC = () => {
  const [confirmationCode, setConfirmationCode] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const navigate = useNavigate();
  const location = useLocation();
  const email = location.state?.email || '';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    if (!email) {
      setError('Email is required. Please go back to registration.');
      return;
    }

    if (confirmationCode.length !== 6) {
      setError('Confirmation code must be 6 digits');
      return;
    }

    setIsLoading(true);

    try {
      const response = await api.auth.confirmSignUp({
        email,
        confirmationCode: confirmationCode,
      });

      setSuccess(response.message);
      
      // Redirect to login after successful confirmation
      setTimeout(() => {
        navigate('/login');
      }, 2000);
    } catch (error) {
      console.error('Confirmation error:', error);
      setError(error instanceof Error ? error.message : 'Confirmation failed. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-background px-4 sm:px-6 lg:px-8">
      <Card className="w-full max-w-md" data-testid="confirm-signup-card">
        <CardHeader className="space-y-4">
          <div className="flex justify-center">
            <Logo width={180} height={54} className="h-12" />
          </div>
          <div className="space-y-1" data-testid="confirm-signup-header">
            <CardTitle className="text-2xl font-bold text-center" data-testid="confirm-signup-title">Confirm Your Account</CardTitle>
            <CardDescription className="text-center" data-testid="confirm-signup-description">
              We've sent a confirmation code to your email address
            </CardDescription>
          </div>
        </CardHeader>
        <CardContent>
          {email && (
            <div className="mb-4 p-3 bg-primary/10 rounded-md" data-testid="email-sent-message">
              <p className="text-sm text-primary" data-testid="confirmation-email">
                Confirmation code sent to: <strong>{email}</strong>
              </p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4" data-testid="confirm-signup-form">
            <div className="space-y-2">
              <Label htmlFor="confirmationCode">Confirmation Code</Label>
              <Input
                id="confirmationCode"
                type="text"
                placeholder="Enter 6-digit code"
                value={confirmationCode}
                onChange={(e) => setConfirmationCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                required
                disabled={isLoading}
                maxLength={6}
                className="text-center text-lg tracking-widest"
                data-testid="confirmation-code-input"
              />
              <p className="text-xs text-muted-foreground">
                Check your email for the 6-digit confirmation code
              </p>
            </div>

            {error && (
              <div className="text-sm text-destructive bg-destructive/10 p-3 rounded-md" data-testid="confirm-signup-error">
                {error}
              </div>
            )}

            {success && (
              <div className="text-sm text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-950/20 p-3 rounded-md" data-testid="confirm-signup-success">
                {success}
              </div>
            )}

            <Button
              type="submit"
              className="w-full"
              disabled={isLoading || confirmationCode.length !== 6}
              data-testid="confirm-signup-submit"
            >
              {isLoading ? 'Confirming...' : 'Confirm Account'}
            </Button>
          </form>

          <div className="mt-6 text-center space-y-2">
            <p className="text-sm text-muted-foreground">
              Didn't receive the code?{' '}
              <button
                type="button"
                className="font-medium text-primary hover:text-primary/80"
                onClick={() => {
                  // TODO: Implement resend confirmation code
                  alert('Resend functionality not implemented yet');
                }}
                data-testid="resend-code-button"
              >
                Resend
              </button>
            </p>
            <p className="text-sm text-muted-foreground">
              <Link
                to="/register"
                className="font-medium text-primary hover:text-primary/80"
                data-testid="back-to-register-link"
              >
                Back to registration
              </Link>
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};
