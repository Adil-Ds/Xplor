import { motion } from "motion/react";
import { Link } from "react-router";
import { Brain, Mail, ArrowLeft } from "lucide-react";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Card } from "../components/ui/card";
import { useState } from "react";

export default function ForgotPasswordPage() {
  const [sent, setSent] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSent(true);
  };

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-8 relative overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-br from-[#070B14] to-[#0F172A]" />
      
      {/* Floating orbs */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute top-1/4 right-1/4 w-96 h-96 bg-blue-500 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-pulse" />
        <div className="absolute bottom-1/4 left-1/4 w-96 h-96 bg-purple-500 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-pulse delay-1000" />
      </div>

      {/* Animated grid */}
      <div className="absolute inset-0 opacity-5" style={{
        backgroundImage: `linear-gradient(rgba(59, 130, 246, 0.5) 1px, transparent 1px), linear-gradient(90deg, rgba(59, 130, 246, 0.5) 1px, transparent 1px)`,
        backgroundSize: '50px 50px'
      }} />

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-md relative z-10"
      >
        <div className="text-center mb-8">
          <Link to="/" className="inline-flex items-center gap-2 mb-8">
            <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl flex items-center justify-center">
              <Brain className="w-7 h-7 text-white" />
            </div>
          </Link>
          
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ delay: 0.2, type: "spring" }}
            className="inline-flex items-center justify-center w-20 h-20 rounded-2xl bg-gradient-to-br from-blue-500/20 to-purple-500/20 border border-blue-500/30 mb-6"
          >
            <Mail className="w-10 h-10 text-blue-400" />
          </motion.div>

          <h2 className="text-3xl font-bold text-white mb-2">
            {sent ? "Check your email" : "Reset your password"}
          </h2>
          <p className="text-white/60">
            {sent 
              ? "We've sent a password reset link to your email address"
              : "Enter your email address and we'll send you a link to reset your password"
            }
          </p>
        </div>

        <Card className="p-8 bg-gradient-to-b from-white/5 to-transparent border-white/10 backdrop-blur-xl">
          {!sent ? (
            <form onSubmit={handleSubmit} className="space-y-6">
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

              <Button 
                type="submit"
                className="w-full bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white"
              >
                Send Reset Link
              </Button>
            </form>
          ) : (
            <div className="space-y-6">
              <div className="rounded-lg bg-green-500/10 border border-green-500/20 p-4">
                <p className="text-green-400 text-sm">
                  If an account exists with this email, you'll receive a password reset link shortly.
                </p>
              </div>

              <Button 
                onClick={() => setSent(false)}
                variant="outline"
                className="w-full border-white/10 bg-white/5 text-white hover:bg-white/10"
              >
                Send Another Link
              </Button>
            </div>
          )}

          <div className="mt-6 pt-6 border-t border-white/10">
            <Link to="/login" className="flex items-center justify-center gap-2 text-white/80 hover:text-white transition-colors">
              <ArrowLeft className="w-4 h-4" />
              Back to sign in
            </Link>
          </div>
        </Card>
      </motion.div>
    </div>
  );
}
