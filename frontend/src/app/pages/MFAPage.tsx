import { motion } from "motion/react";
import { Link, useNavigate } from "react-router";
import { Brain, Shield } from "lucide-react";
import { Button } from "../components/ui/button";
import { Card } from "../components/ui/card";
import { InputOTP, InputOTPGroup, InputOTPSlot } from "../components/ui/input-otp";
import { useState } from "react";

export default function MFAPage() {
  const [value, setValue] = useState("");
  const navigate = useNavigate();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (value.length === 6) {
      navigate("/dashboard");
    }
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
            <Shield className="w-10 h-10 text-blue-400" />
          </motion.div>

          <h2 className="text-3xl font-bold text-white mb-2">Two-Factor Authentication</h2>
          <p className="text-white/60">
            Enter the 6-digit code from your authenticator app
          </p>
        </div>

        <Card className="p-8 bg-gradient-to-b from-white/5 to-transparent border-white/10 backdrop-blur-xl">
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="flex justify-center">
              <InputOTP
                maxLength={6}
                value={value}
                onChange={(value) => setValue(value)}
              >
                <InputOTPGroup>
                  <InputOTPSlot index={0} className="w-12 h-14 text-2xl bg-white/5 border-white/10 text-white" />
                  <InputOTPSlot index={1} className="w-12 h-14 text-2xl bg-white/5 border-white/10 text-white" />
                  <InputOTPSlot index={2} className="w-12 h-14 text-2xl bg-white/5 border-white/10 text-white" />
                  <InputOTPSlot index={3} className="w-12 h-14 text-2xl bg-white/5 border-white/10 text-white" />
                  <InputOTPSlot index={4} className="w-12 h-14 text-2xl bg-white/5 border-white/10 text-white" />
                  <InputOTPSlot index={5} className="w-12 h-14 text-2xl bg-white/5 border-white/10 text-white" />
                </InputOTPGroup>
              </InputOTP>
            </div>

            <Button 
              type="submit"
              className="w-full bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white"
              disabled={value.length !== 6}
            >
              Verify & Continue
            </Button>

            <div className="text-center">
              <button
                type="button"
                className="text-sm text-blue-400 hover:text-blue-300 transition-colors"
              >
                Didn't receive the code? Resend
              </button>
            </div>
          </form>
        </Card>

        <p className="mt-6 text-center text-white/60 text-sm">
          Having trouble?{" "}
          <button type="button" onClick={() => window.alert('Backup code feature will be available soon')} className="text-blue-400 hover:text-blue-300 underline cursor-pointer">
            Use backup code
          </button>
        </p>
      </motion.div>
    </div>
  );
}
