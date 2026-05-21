import { motion } from "motion/react";
import { ReactNode } from "react";

interface ButtonProps {
  children: ReactNode;
  variant?: "primary" | "secondary" | "ghost";
  onClick?: () => void;
  className?: string;
  icon?: ReactNode;
}

export default function Button({ 
  children, 
  variant = "primary", 
  onClick, 
  className = "",
  icon
}: ButtonProps) {
  const baseStyles = "px-6 py-3 rounded-xl flex items-center gap-2 transition-all duration-300";
  
  const variants = {
    primary: "bg-gradient-to-r from-cyan-500 to-blue-500 text-white shadow-lg shadow-cyan-500/50 hover:shadow-cyan-500/70",
    secondary: "bg-white/10 text-white border border-white/20 hover:bg-white/20",
    ghost: "text-white hover:bg-white/10"
  };

  return (
    <motion.button
      className={`${baseStyles} ${variants[variant]} ${className}`}
      onClick={onClick}
      whileHover={{ scale: 1.05 }}
      whileTap={{ scale: 0.95 }}
    >
      {icon}
      {children}
    </motion.button>
  );
}
