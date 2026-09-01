import { motion } from "motion/react";
import { Shield, AlertTriangle, TrendingUp } from "lucide-react";
import { Card } from "../../components/ui/card";
import { Progress } from "../../components/ui/progress";

export default function RiskEngine() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-4xl font-bold text-white mb-2">Risk Score Engine</h1>
        <p className="text-white/60">AI-powered risk assessment and scoring</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="p-6 bg-gradient-to-b from-white/5 to-transparent border-white/10">
          <div className="flex items-center justify-center mb-4">
            <div className="relative w-32 h-32">
              <svg className="transform -rotate-90 w-32 h-32">
                <circle cx="64" cy="64" r="56" stroke="rgba(255,255,255,0.1)" strokeWidth="12" fill="none" />
                <circle cx="64" cy="64" r="56" stroke="#10B981" strokeWidth="12" fill="none" strokeDasharray={`${(85 / 100) * 352} 352`} strokeLinecap="round" />
              </svg>
              <div className="absolute inset-0 flex items-center justify-center flex-col">
                <span className="text-4xl font-bold text-white">85</span>
                <span className="text-white/60 text-sm">Low Risk</span>
              </div>
            </div>
          </div>
          <h3 className="text-center text-white font-semibold">Overall Risk Score</h3>
        </Card>

        {[
          { label: "Data Quality Risk", value: 92, color: "text-green-400" },
          { label: "Security Risk", value: 78, color: "text-yellow-400" },
          { label: "Compliance Risk", value: 95, color: "text-green-400" },
        ].map((risk, index) => (
          <Card key={index} className="p-6 bg-gradient-to-b from-white/5 to-transparent border-white/10">
            <div className="mb-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-white">{risk.label}</span>
                <span className={`text-2xl font-bold ${risk.color}`}>{risk.value}</span>
              </div>
              <Progress value={risk.value} className="h-2" />
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
