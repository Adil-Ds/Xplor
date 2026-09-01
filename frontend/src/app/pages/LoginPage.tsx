import { motion } from "motion/react";
import { Link } from "react-router";
import { Brain, Lock, Mail, Github } from "lucide-react";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Card } from "../components/ui/card";

export default function LoginPage() {
  return (
    <div className="min-h-screen bg-background flex">
      {/* Left side - Illustration */}
      <div className="hidden lg:flex lg:w-1/2 relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-blue-600 via-purple-600 to-pink-600" />
        <div className="absolute inset-0 opacity-30">
          <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-white rounded-full mix-blend-overlay filter blur-3xl animate-pulse" />
          <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-cyan-400 rounded-full mix-blend-overlay filter blur-3xl animate-pulse delay-1000" />
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
            <h1 className="text-4xl font-bold mb-4">Welcome Back to Xplore</h1>
            <p className="text-white/80 text-lg max-w-md">
              Enterprise-grade AI analytics platform trusted by thousands of teams worldwide
            </p>
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
          <div className="absolute top-1/4 right-1/4 w-64 h-64 bg-blue-500 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-pulse" />
          <div className="absolute bottom-1/4 left-1/4 w-64 h-64 bg-purple-500 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-pulse delay-1000" />
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
            <h2 className="text-3xl font-bold text-white mb-2">Sign in to your account</h2>
            <p className="text-white/60">Enter your credentials to access your dashboard</p>
          </div>

          <Card className="p-8 bg-gradient-to-b from-white/5 to-transparent border-white/10 backdrop-blur-xl">
            <form className="space-y-6">
              <div>
                <Label htmlFor="email" className="text-white mb-2 block">Email Address</Label>
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
                <div className="flex items-center justify-between mb-2">
                  <Label htmlFor="password" className="text-white">Password</Label>
                  <Link to="/forgot-password" className="text-sm text-blue-400 hover:text-blue-300 transition-colors">
                    Forgot password?
                  </Link>
                </div>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-white/40" />
                  <Input
                    id="password"
                    type="password"
                    placeholder="••••••••"
                    className="pl-11 bg-white/5 border-white/10 text-white placeholder:text-white/40 focus:border-blue-500 focus:ring-blue-500"
                  />
                </div>
              </div>

              <div className="flex items-center">
                <input
                  id="remember"
                  type="checkbox"
                  className="w-4 h-4 rounded border-white/20 bg-white/5 text-blue-500 focus:ring-blue-500 focus:ring-offset-0"
                />
                <label htmlFor="remember" className="ml-2 text-sm text-white/80">
                  Remember me for 30 days
                </label>
              </div>

              <Link to="/dashboard">
                <Button className="w-full bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white">
                  Sign In
                </Button>
              </Link>

              <div className="relative">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-white/10" />
                </div>
                <div className="relative flex justify-center text-sm">
                  <span className="px-2 bg-transparent text-white/60">Or continue with</span>
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
            Don't have an account?{" "}
            <Link to="/signup" className="text-blue-400 hover:text-blue-300 font-semibold">
              Sign up for free
            </Link>
          </p>
        </motion.div>
      </div>
    </div>
  );
}
