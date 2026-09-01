import { motion } from "motion/react";
import { Link } from "react-router";
import { Brain, Lock, Mail, User, Github, Building } from "lucide-react";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Card } from "../components/ui/card";
import { useState } from "react";

export default function SignupPage() {
  const [password, setPassword] = useState("");

  const getPasswordStrength = () => {
    if (!password) return { strength: 0, label: "", color: "" };
    if (password.length < 6) return { strength: 25, label: "Weak", color: "bg-red-500" };
    if (password.length < 10) return { strength: 50, label: "Fair", color: "bg-yellow-500" };
    if (password.length < 14) return { strength: 75, label: "Good", color: "bg-blue-500" };
    return { strength: 100, label: "Strong", color: "bg-green-500" };
  };

  const passwordStrength = getPasswordStrength();

  return (
    <div className="min-h-screen bg-background flex">
      {/* Left side - Illustration */}
      <div className="hidden lg:flex lg:w-1/2 relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-purple-600 via-blue-600 to-cyan-600" />
        <div className="absolute inset-0 opacity-30">
          <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-white rounded-full mix-blend-overlay filter blur-3xl animate-pulse" />
          <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-pink-400 rounded-full mix-blend-overlay filter blur-3xl animate-pulse delay-1000" />
        </div>
        
        <div className="relative z-10 flex flex-col items-center justify-center w-full p-12 text-white">
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.8 }}
            className="text-center"
          >
            <div className="w-20 h-20 bg-white/20 backdrop-blur-xl rounded-2xl flex items-center justify-center mb-8 mx-auto">
              <Brain className="w-12 h-12" />
            </div>
            <h1 className="text-4xl font-bold mb-4">Start Your AI Journey Today</h1>
            <p className="text-white/80 text-lg max-w-md">
              Join thousands of teams using Xplore to transform their data workflows
            </p>
            
            <div className="mt-12 space-y-4 text-left max-w-md">
              {[
                "Advanced AI-powered analytics",
                "Enterprise-grade security",
                "Real-time threat detection",
                "Natural language querying"
              ].map((feature, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.3 + i * 0.1 }}
                  className="flex items-center gap-3"
                >
                  <div className="w-6 h-6 rounded-full bg-white/20 flex items-center justify-center flex-shrink-0">
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                  <span>{feature}</span>
                </motion.div>
              ))}
            </div>
          </motion.div>
        </div>

        {/* Animated grid */}
        <div className="absolute inset-0 opacity-10" style={{
          backgroundImage: `linear-gradient(white 1px, transparent 1px), linear-gradient(90deg, white 1px, transparent 1px)`,
          backgroundSize: '50px 50px'
        }} />
      </div>

      {/* Right side - Form */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-8 relative">
        <div className="absolute inset-0 bg-gradient-to-br from-[#070B14] to-[#0F172A]" />
        
        {/* Floating orbs */}
        <div className="absolute inset-0 overflow-hidden">
          <div className="absolute top-1/4 right-1/4 w-64 h-64 bg-purple-500 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-pulse" />
          <div className="absolute bottom-1/4 left-1/4 w-64 h-64 bg-blue-500 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-pulse delay-1000" />
        </div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="w-full max-w-md relative z-10"
        >
          <div className="mb-8">
            <Link to="/" className="inline-flex items-center gap-2 mb-8 group">
              <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
                <Brain className="w-6 h-6 text-white" />
              </div>
              <span className="text-xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
                Xplore
              </span>
            </Link>
            <h2 className="text-3xl font-bold text-white mb-2">Create your account</h2>
            <p className="text-white/60">Start your free trial, no credit card required</p>
          </div>

          <Card className="p-8 bg-gradient-to-b from-white/5 to-transparent border-white/10 backdrop-blur-xl">
            <form className="space-y-5">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="firstName" className="text-white mb-2 block">First Name</Label>
                  <Input
                    id="firstName"
                    type="text"
                    placeholder="John"
                    className="bg-white/5 border-white/10 text-white placeholder:text-white/40 focus:border-blue-500 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <Label htmlFor="lastName" className="text-white mb-2 block">Last Name</Label>
                  <Input
                    id="lastName"
                    type="text"
                    placeholder="Doe"
                    className="bg-white/5 border-white/10 text-white placeholder:text-white/40 focus:border-blue-500 focus:ring-blue-500"
                  />
                </div>
              </div>

              <div>
                <Label htmlFor="company" className="text-white mb-2 block">Company Name</Label>
                <div className="relative">
                  <Building className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-white/40" />
                  <Input
                    id="company"
                    type="text"
                    placeholder="Acme Inc."
                    className="pl-11 bg-white/5 border-white/10 text-white placeholder:text-white/40 focus:border-blue-500 focus:ring-blue-500"
                  />
                </div>
              </div>

              <div>
                <Label htmlFor="email" className="text-white mb-2 block">Work Email</Label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-white/40" />
                  <Input
                    id="email"
                    type="email"
                    placeholder="you@company.com"
                    className="pl-11 bg-white/5 border-white/10 text-white placeholder:text-white/40 focus:border-blue-500 focus:ring-blue-500"
                  />
                </div>
              </div>

              <div>
                <Label htmlFor="password" className="text-white mb-2 block">Password</Label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-white/40" />
                  <Input
                    id="password"
                    type="password"
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="pl-11 bg-white/5 border-white/10 text-white placeholder:text-white/40 focus:border-blue-500 focus:ring-blue-500"
                  />
                </div>
                {password && (
                  <div className="mt-2">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs text-white/60">Password strength</span>
                      <span className={`text-xs ${passwordStrength.color.replace('bg-', 'text-')}`}>
                        {passwordStrength.label}
                      </span>
                    </div>
                    <div className="h-1.5 bg-white/10 rounded-full overflow-hidden">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${passwordStrength.strength}%` }}
                        className={`h-full ${passwordStrength.color} transition-all duration-300`}
                      />
                    </div>
                  </div>
                )}
              </div>

              <div className="flex items-start">
                <input
                  id="terms"
                  type="checkbox"
                  className="w-4 h-4 rounded border-white/20 bg-white/5 text-blue-500 focus:ring-blue-500 focus:ring-offset-0 mt-0.5"
                />
                <label htmlFor="terms" className="ml-2 text-sm text-white/80">
                  I agree to the{" "}
                  <button type="button" onClick={() => window.alert('Terms of Service will be available soon')} className="text-blue-400 hover:text-blue-300 underline cursor-pointer">Terms of Service</button>
                  {" "}and{" "}
                  <button type="button" onClick={() => window.alert('Privacy Policy will be available soon')} className="text-blue-400 hover:text-blue-300 underline cursor-pointer">Privacy Policy</button>
                </label>
              </div>

              <Link to="/mfa">
                <Button className="w-full bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white">
                  Create Account
                </Button>
              </Link>

              <div className="relative">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-white/10" />
                </div>
                <div className="relative flex justify-center text-sm">
                  <span className="px-2 bg-transparent text-white/60">Or sign up with</span>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <Button variant="outline" className="border-white/10 bg-white/5 text-white hover:bg-white/10">
                  <Github className="w-5 h-5 mr-2" />
                  GitHub
                </Button>
                <Button variant="outline" className="border-white/10 bg-white/5 text-white hover:bg-white/10">
                  <svg className="w-5 h-5 mr-2" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09zM12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98 1.06-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23zM5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63zM12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z" />
                  </svg>
                  Google
                </Button>
              </div>
            </form>
          </Card>

          <p className="mt-6 text-center text-white/60">
            Already have an account?{" "}
            <Link to="/login" className="text-blue-400 hover:text-blue-300 font-semibold">
              Sign in
            </Link>
          </p>
        </motion.div>
      </div>
    </div>
  );
}
