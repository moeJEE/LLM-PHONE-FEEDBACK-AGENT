import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useSignIn, useSignUp } from '@clerk/clerk-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { Alert, AlertDescription } from '@/components/ui/alert';

const AuthPage = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [rememberMe, setRememberMe] = useState(false);
  const [acceptTerms, setAcceptTerms] = useState(false);
  
  // Verification states
  const [verificationStep, setVerificationStep] = useState(false);
  const [verificationCode, setVerificationCode] = useState('');
  
  const navigate = useNavigate();
  const { signIn, isLoaded: isSignInLoaded } = useSignIn();
  const { signUp, isLoaded: isSignUpLoaded, setActive } = useSignUp();
  
  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);
    
    try {
      if (!isSignInLoaded) {
        setError("Authentication service is loading. Please try again in a moment.");
        setIsLoading(false);
        return;
      }
      
      const result = await signIn.create({
        identifier: email,
        password,
      });
      
      if (result.status === "complete") {
        await setActive({ session: result.createdSessionId });
        navigate('/dashboard');
      } else {
        console.log("Login result status:", result.status);
        setError("Login failed. Please try again.");
      }
    } catch (err) {
      console.error("Login error details:", err);
      setError(err.errors?.[0]?.message || 'An error occurred during login');
    } finally {
      setIsLoading(false);
    }
  };
  
  const handleSignup = async (e) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);
  
    try {
      if (!isSignUpLoaded) {
        setError("Authentication service is loading. Please try again in a moment.");
        setIsLoading(false);
        return;
      }
      
      if (!verificationStep) {
        // Validation checks
        if (!acceptTerms) {
          setError('Please accept the terms and conditions');
          setIsLoading(false);
          return;
        }
  
        if (password !== confirmPassword) {
          setError('Passwords do not match');
          setIsLoading(false);
          return;
        }
  
        // Create user with email and password
        const signUpAttempt = await signUp.create({
          emailAddress: email,
          password,
          firstName,
          lastName,
        });
  
        // Trigger verification if required
        if (signUpAttempt.status === "missing_requirements" || signUpAttempt.status === "needs_verification") {
          await signUp.prepareEmailAddressVerification({ strategy: "email_code" });
          setVerificationStep(true);
        } else if (signUpAttempt.status === "complete") {
          await setActive({ session: signUpAttempt.createdSessionId });
          navigate("/dashboard");
        }
      } else {
        // Verify email with the code entered by the user
        const result = await signUp.attemptEmailAddressVerification({
          code: verificationCode,
        });
  
        if (result.status === "complete") {
          await setActive({ session: result.createdSessionId });
          navigate("/dashboard");
        } else {
          setError("Verification failed. Please check the code and try again.");
        }
      }
    } catch (err) {
      console.error("Sign up error:", err);
      setError(err.errors?.[0]?.message || "An error occurred during signup");
    } finally {
      setIsLoading(false);
    }
  };
  
  const resetVerification = () => {
    setVerificationStep(false);
    setVerificationCode('');
  };
  
  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold">AI Phone System</h1>
          <p className="text-muted-foreground mt-2">LLM-Enhanced Phone Feedback System</p>
        </div>
        
        <Tabs defaultValue="login" className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="login">Login</TabsTrigger>
            <TabsTrigger value="signup">Sign Up</TabsTrigger>
          </TabsList>
          
          <TabsContent value="login">
            <Card>
              <CardHeader>
                <CardTitle>Welcome back</CardTitle>
                <CardDescription>
                  Enter your credentials to access your account
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {error && (
                  <Alert variant="destructive">
                    <AlertDescription>{error}</AlertDescription>
                  </Alert>
                )}
                <form onSubmit={handleLogin}>
                  <div className="space-y-4">
                    <div className="space-y-2">
                      <Label htmlFor="email">Email</Label>
                      <Input 
                        id="email" 
                        type="email" 
                        placeholder="m@example.com" 
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        required 
                      />
                    </div>
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <Label htmlFor="password">Password</Label>
                        <Button variant="link" className="px-0" onClick={() => navigate('/forgot-password')}>
                          Forgot password?
                        </Button>
                      </div>
                      <Input 
                        id="password" 
                        type="password" 
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        required 
                      />
                    </div>
                    
                    <div className="flex items-center space-x-2">
                      <Checkbox 
                        id="remember" 
                        checked={rememberMe}
                        onCheckedChange={setRememberMe}
                      />
                      <Label
                        htmlFor="remember"
                        className="text-sm font-normal"
                      >
                        Remember me
                      </Label>
                    </div>
                    
                    <Button 
                      type="submit" 
                      className="w-full" 
                      disabled={isLoading}
                    >
                      {isLoading ? "Signing in..." : "Sign in"}
                    </Button>
                  </div>
                </form>
              </CardContent>
            </Card>
          </TabsContent>
          
          <TabsContent value="signup">
            <Card>
              <CardHeader>
                <CardTitle>
                  {verificationStep ? "Verify Your Account" : "Create an account"}
                </CardTitle>
                <CardDescription>
                  {verificationStep 
                    ? "Enter the verification code sent to your email" 
                    : "Enter your information to create an account"}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {error && (
                  <Alert variant="destructive">
                    <AlertDescription>{error}</AlertDescription>
                  </Alert>
                )}
                
                <form onSubmit={handleSignup}>
                  {!verificationStep ? (
                    // Registration form
                    <>
                      <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                          <Label htmlFor="firstName">First name</Label>
                          <Input 
                            id="firstName" 
                            value={firstName}
                            onChange={(e) => setFirstName(e.target.value)}
                            required 
                          />
                        </div>
                        <div className="space-y-2">
                          <Label htmlFor="lastName">Last name</Label>
                          <Input 
                            id="lastName" 
                            value={lastName}
                            onChange={(e) => setLastName(e.target.value)}
                            required 
                          />
                        </div>
                      </div>
                      
                      <div className="space-y-2 mt-4">
                        <Label htmlFor="email_signup">Email</Label>
                        <Input 
                          id="email_signup" 
                          type="email" 
                          placeholder="m@example.com" 
                          value={email}
                          onChange={(e) => setEmail(e.target.value)}
                          required 
                        />
                      </div>
                      
                      <div className="space-y-2 mt-4">
                        <Label htmlFor="password_signup">Password</Label>
                        <Input 
                          id="password_signup" 
                          type="password" 
                          value={password}
                          onChange={(e) => setPassword(e.target.value)}
                          required 
                        />
                      </div>
                      
                      <div className="space-y-2 mt-4">
                        <Label htmlFor="password_confirm">Confirm password</Label>
                        <Input 
                          id="password_confirm" 
                          type="password" 
                          value={confirmPassword}
                          onChange={(e) => setConfirmPassword(e.target.value)}
                          required 
                        />
                      </div>
                      
                      <div className="flex items-center space-x-2 mt-4">
                        <Checkbox 
                          id="terms" 
                          checked={acceptTerms}
                          onCheckedChange={setAcceptTerms}
                          required 
                        />
                        <Label
                          htmlFor="terms"
                          className="text-sm font-normal"
                        >
                          I agree to the{" "}
                          <Button variant="link" className="p-0 h-auto font-normal">
                            terms of service
                          </Button>{" "}
                          and{" "}
                          <Button variant="link" className="p-0 h-auto font-normal">
                            privacy policy
                          </Button>
                        </Label>
                      </div>
                    </>
                  ) : (
                    // Verification form
                    <div className="space-y-4">
                      <Alert>
                        <AlertDescription>
                          We've sent a verification code to your email. Please check your inbox and enter the code below.
                        </AlertDescription>
                      </Alert>
                      
                      <div className="space-y-2">
                        <Label htmlFor="verification_code">Verification Code</Label>
                        <Input 
                          id="verification_code" 
                          value={verificationCode}
                          onChange={(e) => setVerificationCode(e.target.value)}
                          placeholder="Enter the 6-digit code"
                          required 
                        />
                      </div>
                      
                      <div className="text-sm text-center">
                        <Button 
                          variant="link" 
                          type="button"
                          onClick={resetVerification}
                        >
                          Back to registration
                        </Button>
                      </div>
                    </div>
                  )}
                  
                  <Button 
                    type="submit" 
                    className="w-full mt-6" 
                    disabled={isLoading}
                  >
                    {isLoading 
                      ? (verificationStep ? "Verifying..." : "Creating account...") 
                      : (verificationStep ? "Verify Account" : "Create account")}
                  </Button>
                </form>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
        
        <p className="text-center text-sm text-muted-foreground mt-6">
          By using our service, you agree to our Terms of Service and Privacy Policy.
        </p>
      </div>
      <div id="clerk-captcha"></div>
    </div>
  );
};

export default AuthPage;