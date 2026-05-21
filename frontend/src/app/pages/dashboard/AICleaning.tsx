import { motion } from "motion/react";
import { Sparkles, CheckCircle2, AlertCircle, XCircle } from "lucide-react";
import { Card } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Badge } from "../../components/ui/badge";
import { Progress } from "../../components/ui/progress";

const cleaningIssues = [
  { type: "Missing Values", count: 234, severity: "high", fixed: 234, color: "from-yellow-500 to-orange-500" },
  { type: "Duplicate Rows", count: 45, severity: "medium", fixed: 45, color: "from-blue-500 to-cyan-500" },
  { type: "Invalid Formats", count: 89, severity: "high", fixed: 89, color: "from-red-500 to-pink-500" },
  { type: "Outliers", count: 12, severity: "low", fixed: 12, color: "from-green-500 to-emerald-500" },
];

export default function AICleaning() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-4xl font-bold text-white mb-2">AI Data Cleaning</h1>
        <p className="text-white/60">Automatically detect and fix data quality issues</p>
      </div>

      {/* Status Card */}
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
        <Card className="p-8 bg-gradient-to-b from-white/5 to-transparent border-white/10">
          <div className="text-center">
            <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-green-500/20 to-emerald-500/20 flex items-center justify-center mx-auto mb-4">
              <CheckCircle2 className="w-10 h-10 text-green-400" />
            </div>
            <h3 className="text-2xl font-bold text-white mb-2">Dataset Successfully Cleaned!</h3>
            <p className="text-white/60 mb-6">AI has processed and cleaned your dataset. 380 issues resolved.</p>
            <Progress value={100} className="h-3 mb-4" />
            <div className="flex items-center justify-center gap-8 mt-6">
              <div>
                <p className="text-3xl font-bold text-white">380</p>
                <p className="text-white/60 text-sm">Issues Fixed</p>
              </div>
              <div>
                <p className="text-3xl font-bold text-white">99.8%</p>
                <p className="text-white/60 text-sm">Data Quality</p>
              </div>
              <div>
                <p className="text-3xl font-bold text-white">2.4s</p>
                <p className="text-white/60 text-sm">Processing Time</p>
              </div>
            </div>
          </div>
        </Card>
      </motion.div>

      {/* Issues Breakdown */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {cleaningIssues.map((issue, index) => (
          <motion.div
            key={index}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
          >
            <Card className="p-6 bg-gradient-to-b from-white/5 to-transparent border-white/10">
              <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${issue.color} flex items-center justify-center mb-4`}>
                <Sparkles className="w-6 h-6 text-white" />
              </div>
              <h3 className="text-white font-semibold mb-2">{issue.type}</h3>
              <div className="flex items-center justify-between mb-3">
                <span className="text-2xl font-bold text-white">{issue.fixed}/{issue.count}</span>
                <Badge className="bg-green-500/10 text-green-400 border-green-500/20">Fixed</Badge>
              </div>
              <Progress value={(issue.fixed / issue.count) * 100} className="h-2" />
            </Card>
          </motion.div>
        ))}
      </div>

      <Button className="bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white">
        <Sparkles className="w-4 h-4 mr-2" />
        Run AI Cleaning Again
      </Button>
    </div>
  );
}
