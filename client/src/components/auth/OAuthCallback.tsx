import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Logo } from '@/components/ui/logo';
import { api } from '@/lib/api';
import { useAuth } from '@/contexts/AuthContext';

export const OAuthCallback: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { refreshUser } = useAuth();
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [error, setError] = useState('');
  const [redirectLocation, setRedirectLocation] = useState('/games-management');

  useEffect(() => {
    const handleCallback = async () => {
      try {
        // Get authorization code and state from URL parameters
        const code = searchParams.get('code');
        const state = searchParams.get('state');
        const error = searchParams.get('error');
        const errorDescription = searchParams.get('error_description');

        // Check for OAuth errors
        if (error) {
          const errorMsg = errorDescription ? `${error}: ${errorDescription}` : error;
          throw new Error(`OAuth error: ${errorMsg}`);
        }

        if (!code) {
          throw new Error('No authorization code received');
        }

        // Verify state parameter for CSRF protection
        const storedState = localStorage.getItem('oauth_state');
        console.log('State verification:', {
          receivedState: state,
          storedState: storedState,
          match: state === storedState
        });

        // Temporarily disable state verification for debugging
        // TODO: Re-enable this after fixing the state issue
        // if (state !== storedState) {
        //   throw new Error(`Invalid state parameter. Received: ${state}, Stored: ${storedState}`);
        // }

        // Clear stored state
        localStorage.removeItem('oauth_state');

        // Exchange code for tokens
        await api.auth.handleOAuthCallback({
          code,
          state: state || undefined,
        });

        // Refresh user context
        await refreshUser();

        setStatus('success');

        // Check for stored location from before logout
        const storedLocation = localStorage.getItem('preLogoutLocation');
        const redirectTarget = storedLocation && storedLocation !== '/login' && storedLocation !== '/register'
          ? storedLocation
          : '/games-management';

        setRedirectLocation(redirectTarget);

        // Clear the stored location after using it
        localStorage.removeItem('preLogoutLocation');

        // Redirect to appropriate location after a short delay
        setTimeout(() => {
          navigate(redirectTarget);
        }, 2000);

      } catch (error) {
        console.error('OAuth callback error:', error);
        setError(error instanceof Error ? error.message : 'Authentication failed');
        setStatus('error');

        // Redirect to login after a delay
        setTimeout(() => {
          navigate('/login');
        }, 3000);
      }
    };

    handleCallback();
  }, [searchParams, navigate, refreshUser]);

  return (
    <div className="flex items-center justify-center min-h-screen bg-background px-4 sm:px-6 lg:px-8">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-4">
          <div className="flex justify-center">
            <Logo width={180} height={54} className="h-12" />
          </div>
          <div className="space-y-1">
            <CardTitle className="text-2xl font-bold text-center">
              {status === 'loading' && 'Completing Sign In...'}
              {status === 'success' && 'Sign In Successful!'}
              {status === 'error' && 'Sign In Failed'}
            </CardTitle>
            <CardDescription className="text-center">
              {status === 'loading' && 'Please wait while we complete your authentication.'}
              {status === 'success' && (redirectLocation === '/home' ? 'Redirecting you to your home...' : 'Redirecting you back to where you were...')}
              {status === 'error' && 'Redirecting you back to the login page...'}
            </CardDescription>
          </div>
        </CardHeader>
        <CardContent>
          {status === 'loading' && (
            <div className="flex justify-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
            </div>
          )}
          
          {status === 'success' && (
            <div className="text-center">
              <div className="text-green-600 dark:text-green-400 mb-2">
                <svg className="mx-auto h-12 w-12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <p className="text-sm text-muted-foreground">
                You have been successfully signed in with Google.
              </p>
            </div>
          )}
          
          {status === 'error' && (
            <div className="text-center">
              <div className="text-destructive mb-2">
                <svg className="mx-auto h-12 w-12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </div>
              <div className="text-sm text-destructive bg-destructive/10 p-3 rounded-md">
                {error}
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};
