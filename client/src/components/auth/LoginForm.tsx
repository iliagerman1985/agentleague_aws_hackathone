import React, { useState, useEffect, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Logo } from '@/components/ui/logo';
import { useAuth } from '@/contexts/AuthContext';
import { api } from '@/lib/api';
import Galaxy from '@/components/Galaxy';

export const LoginForm: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const errorRef = useRef('');

  const { signIn } = useAuth();
  const navigate = useNavigate();

  // Keep ref in sync with state
  useEffect(() => {
    errorRef.current = error;
  }, [error]);

  // Load remembered credentials on component mount
  useEffect(() => {
    const rememberedEmail = localStorage.getItem('rememberedEmail');
    const rememberedPassword = localStorage.getItem('rememberedPassword');
    if (rememberedEmail) {
      setEmail(rememberedEmail);
      setRememberMe(true);
      
      // Decode the stored password if it exists
      if (rememberedPassword) {
        try {
          const decodedPassword = atob(rememberedPassword);
          setPassword(decodedPassword);
        } catch (error) {
          console.warn('Failed to decode remembered password, clearing it');
          localStorage.removeItem('rememberedPassword');
        }
      }
    }
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      await signIn(email, password);

      // Clear any previous errors on success
      setError('');
      errorRef.current = '';

      // Clear DOM error container as well
      const errorContainer = document.querySelector('[data-error-container]');
      if (errorContainer) {
        errorContainer.innerHTML = '';
      }

      // Handle remember me functionality
      if (rememberMe) {
        localStorage.setItem('rememberedEmail', email);
        // Note: Storing password in localStorage is a security risk but requested by user
        // Using basic encoding to make it less obvious in storage
        localStorage.setItem('rememberedPassword', btoa(password));
      } else {
        localStorage.removeItem('rememberedEmail');
        localStorage.removeItem('rememberedPassword');
      }

      // Check for stored location from before logout
      const storedLocation = localStorage.getItem('preLogoutLocation');
      const redirectLocation = storedLocation && storedLocation !== '/login' && storedLocation !== '/register'
        ? storedLocation
        : '/games-management';

      // Clear the stored location after using it
      localStorage.removeItem('preLogoutLocation');

      navigate(redirectLocation);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Login failed. Please try again.';
      setError(errorMessage);
      errorRef.current = errorMessage;

      // Also set the error directly in the DOM as a fallback for React state issues
      setTimeout(() => {
        const errorContainer = document.querySelector('[data-error-container]');
        if (errorContainer && errorMessage) {
          errorContainer.innerHTML = `<div class="text-sm text-destructive bg-destructive/10 p-3 rounded-md" data-testid="login-error">${errorMessage}</div>`;
        }
      }, 100);
    } finally {
      setIsLoading(false);
    }
  };

  const handleGoogleSignIn = async () => {
    try {
      setIsLoading(true);
      setError('');

      // Get Google OAuth URL
      const { oauthUrl: oauth_url, state } = await api.auth.getGoogleOAuthUrl();

      console.log('Storing OAuth state:', state);

      // Store state for verification
      localStorage.setItem('oauth_state', state);

      // Redirect to Google OAuth
      window.location.href = oauth_url;
    } catch (error) {
      console.error('Google sign in error:', error);
      setError(error instanceof Error ? error.message : 'Failed to initiate Google sign in');
      setIsLoading(false);
    }
  };

  return (
    <div className="dark relative flex items-center justify-center min-h-screen overflow-hidden bg-background px-4 sm:px-6 lg:px-8">
      {/* Galaxy animation background */}
      <div className="pointer-events-none md:pointer-events-auto" style={{ position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh', zIndex: 0 }} aria-hidden="true">
        <Galaxy
          mouseInteraction={true}
          mouseRepulsion={true}
          density={1}
          glowIntensity={0.2}
          saturation={0.6}
          hueShift={0}
          twinkleIntensity={0.3}
          rotationSpeed={0.1}
          repulsionStrength={1.5}
          autoCenterRepulsion={0}
          starSpeed={0.4}
          speed={0.5}
        />
      </div>

      <Card className="relative z-10 w-full max-w-md login-card-dark animate-loginPop will-change-transform">
          <CardHeader className="space-y-4">
          <div className="flex justify-center">
            <Logo
              width={520}
              height={156}
              color="none"
              className="h-40"
              animated={true}
            />
          </div>
          <div className="space-y-1">
            <CardTitle className="text-2xl font-bold text-center text-foreground">Welcome Back</CardTitle>
            <CardDescription className="text-center text-muted-foreground">
              Enter your credentials to access your account.
            </CardDescription>
          </div>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4" data-testid="login-form">
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                placeholder="Enter your email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                disabled={isLoading}
                data-testid="email-input"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                placeholder="Enter your password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                disabled={isLoading}
                data-testid="password-input"
              />
            </div>

            <div className="flex items-center space-x-2">
              <Checkbox
                id="remember-me"
                checked={rememberMe}
                onCheckedChange={(checked) => setRememberMe(checked as boolean)}
                disabled={isLoading}
                data-testid="remember-me-checkbox"
              />
              <Label
                htmlFor="remember-me"
                className="text-sm font-normal cursor-pointer"
                data-testid="remember-me-label"
              >
                Remember my credentials
              </Label>
            </div>

            {(error || errorRef.current) && (
              <div className="text-sm text-destructive bg-destructive/10 p-3 rounded-md" data-testid="login-error">
                {error || errorRef.current}
              </div>
            )}

            {/* Fallback error container for DOM manipulation */}
            <div data-error-container></div>

            <Button
              type="submit"
              className="w-full"
              disabled={isLoading}
              data-testid="login-submit-button"
            >
              {isLoading ? 'Signing In...' : 'Sign In'}
            </Button>
          </form>

          <div className="mt-6">
            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <span className="w-full border-t" />
              </div>
              <div className="relative flex justify-center text-xs uppercase">
                <span className="bg-background px-2 text-muted-foreground">
                  Or continue with
                </span>
              </div>
            </div>

            <Button
              type="button"
              variant="outline"
              className="w-full mt-4"
              disabled={isLoading}
              onClick={handleGoogleSignIn}
              data-testid="google-signin-button"
            >
              <svg className="mr-2 h-4 w-4" viewBox="0 0 24 24">
                <path
                  d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                  fill="#4285F4"
                />
                <path
                  d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                  fill="#34A853"
                />
                <path
                  d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                  fill="#FBBC05"
                />
                <path
                  d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                  fill="#EA4335"
                />
              </svg>
              Continue with Google
            </Button>
          </div>

          <div className="mt-6 text-center">
            <p className="text-sm text-muted-foreground">
              Don't have an account?{' '}
              <Link
                to="/register"
                className="font-medium text-primary hover:text-primary/80"
              >
                Sign up
              </Link>
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};
