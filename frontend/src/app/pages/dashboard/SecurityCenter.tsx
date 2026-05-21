import { motion } from "motion/react";
import { 
  Shield, 
  AlertTriangle, 
  Lock,
  Eye,
  Activity,
  Globe,
  ArrowUp,
  ArrowDown,
  AlertCircle,
  CheckCircle2,
  XCircle
} from "lucide-react";
import { Card } from "../../components/ui/card";
import { Badge } from "../../components/ui/badge";
import { Progress } from "../../components/ui/progress";
import { RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, ResponsiveContainer, XAxis, YAxis, CartesianGrid, Tooltip, AreaChart, Area } from "recharts";

const securityMetrics = [
  { id: "metric-0", category: "Encryption", score: 98 },
  { id: "metric-1", category: "Access Control", score: 95 },
  { id: "metric-2", category: "Network Security", score: 92 },
  { id: "metric-3", category: "Data Privacy", score: 97 },
  { id: "metric-4", category: "Threat Detection", score: 94 },
  { id: "metric-5", category: "Compliance", score: 99 },
];

const liveThreats = [
  { id: 1, type: "SQL Injection Attempt", severity: "critical", source: "192.168.1.45", time: "2 min ago", status: "blocked" },
  { id: 2, type: "Unauthorized Access", severity: "high", source: "203.45.12.89", time: "5 min ago", status: "blocked" },
  { id: 3, type: "DDoS Attack Pattern", severity: "medium", source: "Multiple IPs", time: "8 min ago", status: "monitoring" },
  { id: 4, type: "Suspicious API Calls", severity: "medium", source: "10.0.0.23", time: "12 min ago", status: "investigating" },
  { id: 5, type: "Brute Force Login", severity: "high", source: "156.78.90.12", time: "15 min ago", status: "blocked" },
];

const threatTimeline = [
  { id: "timeline-0", time: "00:00", threats: 2 },
  { id: "timeline-1", time: "04:00", threats: 1 },
  { id: "timeline-2", time: "08:00", threats: 5 },
  { id: "timeline-3", time: "12:00", threats: 3 },
  { id: "timeline-4", time: "16:00", threats: 7 },
  { id: "timeline-5", time: "20:00", threats: 4 },
  { id: "timeline-6", time: "24:00", threats: 2 },
];

const securityScoreHistory = [
  { id: "history-0", date: "Mon", score: 94 },
  { id: "history-1", date: "Tue", score: 96 },
  { id: "history-2", date: "Wed", score: 95 },
  { id: "history-3", date: "Thu", score: 97 },
  { id: "history-4", date: "Fri", score: 98 },
  { id: "history-5", date: "Sat", score: 98 },
  { id: "history-6", date: "Sun", score: 98.5 },
];

const piiDetections = [
  { dataset: "Customer_Data_Q1", instances: 42, type: "Email, Phone", risk: "High" },
  { dataset: "Employee_Records", instances: 28, type: "SSN, Address", risk: "Critical" },
  { dataset: "Sales_Transactions", instances: 15, type: "Credit Card", risk: "Critical" },
  { dataset: "User_Profiles", instances: 8, type: "Email", risk: "Medium" },
];

const encryptionStatus = [
  { name: "AES-256 Active", status: true, coverage: 100 },
  { name: "At-Rest Encryption", status: true, coverage: 100 },
  { name: "In-Transit TLS 1.3", status: true, coverage: 100 },
  { name: "Key Rotation", status: true, coverage: 95 },
];

const getSeverityColor = (severity: string) => {
  switch (severity) {
    case "critical": return "text-red-400 bg-red-500/10 border-red-500/20";
    case "high": return "text-orange-400 bg-orange-500/10 border-orange-500/20";
    case "medium": return "text-yellow-400 bg-yellow-500/10 border-yellow-500/20";
    case "low": return "text-green-400 bg-green-500/10 border-green-500/20";
    default: return "text-gray-400 bg-gray-500/10 border-gray-500/20";
  }
};

const getStatusColor = (status: string) => {
  switch (status) {
    case "blocked": return "text-green-400";
    case "monitoring": return "text-yellow-400";
    case "investigating": return "text-blue-400";
    default: return "text-gray-400";
  }
};

export default function SecurityCenter() {
  const overallScore = 98.5;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-bold text-white mb-2">Security Center</h1>
          <p className="text-white/60">Real-time threat monitoring and security analytics</p>
        </div>
        <div className="flex items-center gap-3 px-6 py-3 rounded-xl bg-gradient-to-r from-green-500/10 to-emerald-500/10 border border-green-500/20">
          <Activity className="w-6 h-6 text-green-400 animate-pulse" />
          <div>
            <p className="text-xs text-green-400/80">System Status</p>
            <p className="text-lg font-bold text-green-400">All Systems Operational</p>
          </div>
        </div>
      </div>

      {/* Top Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        {[
          { icon: Shield, label: "Security Score", value: overallScore.toFixed(1), change: "+2.3%", up: true, color: "from-green-500 to-emerald-500" },
          { icon: AlertTriangle, label: "Active Threats", value: "5", change: "-12", up: true, color: "from-red-500 to-orange-500" },
          { icon: Eye, label: "Monitored Endpoints", value: "1,247", change: "+45", up: true, color: "from-blue-500 to-cyan-500" },
          { icon: Lock, label: "Encryption Coverage", value: "100%", change: "Stable", up: true, color: "from-purple-500 to-pink-500" },
        ].map((metric, index) => (
          <motion.div
            key={index}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
          >
            <Card className="p-6 bg-gradient-to-b from-white/5 to-transparent border-white/10 relative overflow-hidden group">
              <div className={`absolute top-0 right-0 w-32 h-32 bg-gradient-to-br ${metric.color} opacity-10 blur-3xl group-hover:opacity-20 transition-opacity`} />
              
              <div className="relative">
                <div className="flex items-center justify-between mb-4">
                  <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${metric.color} flex items-center justify-center`}>
                    <metric.icon className="w-6 h-6 text-white" />
                  </div>
                  <div className={`flex items-center gap-1 text-sm ${metric.up ? "text-green-400" : "text-red-400"}`}>
                    {metric.up ? <ArrowUp className="w-4 h-4" /> : <ArrowDown className="w-4 h-4" />}
                    <span>{metric.change}</span>
                  </div>
                </div>
                <div>
                  <p className="text-white/60 text-sm">{metric.label}</p>
                  <p className="text-3xl font-bold text-white">{metric.value}</p>
                </div>
              </div>
            </Card>
          </motion.div>
        ))}
      </div>

      {/* Security Radar & Score History */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Security Radar */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.3 }}
        >
          <Card className="p-6 bg-gradient-to-b from-white/5 to-transparent border-white/10 h-full">
            <div className="mb-6">
              <h3 className="text-xl font-semibold text-white mb-1">Security Posture</h3>
              <p className="text-white/60 text-sm">Multi-dimensional security analysis</p>
            </div>
            <ResponsiveContainer width="100%" height={350}>
              <RadarChart data={securityMetrics} id="security-metrics-radar">
                <PolarGrid stroke="rgba(255,255,255,0.1)" />
                <PolarAngleAxis dataKey="category" stroke="rgba(255,255,255,0.6)" />
                <PolarRadiusAxis stroke="rgba(255,255,255,0.4)" domain={[0, 100]} />
                <Radar name="Score" dataKey="score" stroke="#3B82F6" fill="#3B82F6" fillOpacity={0.3} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "rgba(15, 23, 42, 0.95)",
                    border: "1px solid rgba(255,255,255,0.1)",
                    borderRadius: "8px",
                    color: "#fff"
                  }}
                />
              </RadarChart>
            </ResponsiveContainer>
          </Card>
        </motion.div>

        {/* Score History */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.4 }}
        >
          <Card className="p-6 bg-gradient-to-b from-white/5 to-transparent border-white/10 h-full">
            <div className="mb-6">
              <h3 className="text-xl font-semibold text-white mb-1">Security Score Trend</h3>
              <p className="text-white/60 text-sm">Weekly performance tracking</p>
            </div>
            <ResponsiveContainer width="100%" height={350}>
              <AreaChart data={securityScoreHistory} id="security-score-trend">
                <defs>
                  <linearGradient id="scoreGradient-security" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10B981" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#10B981" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="date" stroke="rgba(255,255,255,0.4)" />
                <YAxis stroke="rgba(255,255,255,0.4)" domain={[90, 100]} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "rgba(15, 23, 42, 0.95)",
                    border: "1px solid rgba(255,255,255,0.1)",
                    borderRadius: "8px",
                    color: "#fff"
                  }}
                />
                <Area type="monotone" dataKey="score" stroke="#10B981" fill="url(#scoreGradient-security)" strokeWidth={3} name="Security Score" />
              </AreaChart>
            </ResponsiveContainer>
          </Card>
        </motion.div>
      </div>

      {/* Live Threat Feed */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5 }}
      >
        <Card className="p-6 bg-gradient-to-b from-white/5 to-transparent border-white/10">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h3 className="text-xl font-semibold text-white mb-1">Live Threat Feed</h3>
              <p className="text-white/60 text-sm">Real-time security event monitoring</p>
            </div>
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-red-500/10 border border-red-500/20">
              <div className="w-2 h-2 bg-red-400 rounded-full animate-pulse" />
              <span className="text-sm text-red-400">Live</span>
            </div>
          </div>

          <div className="space-y-3">
            {liveThreats.map((threat, index) => (
              <motion.div
                key={threat.id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.6 + index * 0.1 }}
                className="flex items-center gap-4 p-4 rounded-xl bg-white/5 hover:bg-white/10 transition-all border border-white/5 hover:border-white/10"
              >
                <div className={`w-2 h-2 rounded-full ${
                  threat.severity === "critical" ? "bg-red-500" :
                  threat.severity === "high" ? "bg-orange-500" :
                  threat.severity === "medium" ? "bg-yellow-500" : "bg-green-500"
                } animate-pulse`} />
                
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3 mb-1">
                    <p className="text-white font-medium">{threat.type}</p>
                    <Badge variant="outline" className={getSeverityColor(threat.severity)}>
                      {threat.severity.toUpperCase()}
                    </Badge>
                  </div>
                  <div className="flex items-center gap-4 text-sm text-white/60">
                    <span className="flex items-center gap-1">
                      <Globe className="w-3 h-3" />
                      {threat.source}
                    </span>
                    <span>{threat.time}</span>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <Badge className={`${getStatusColor(threat.status)} bg-transparent border-0`}>
                    {threat.status === "blocked" && <CheckCircle2 className="w-4 h-4 mr-1" />}
                    {threat.status === "monitoring" && <Eye className="w-4 h-4 mr-1" />}
                    {threat.status === "investigating" && <AlertCircle className="w-4 h-4 mr-1" />}
                    {threat.status.charAt(0).toUpperCase() + threat.status.slice(1)}
                  </Badge>
                </div>
              </motion.div>
            ))}
          </div>
        </Card>
      </motion.div>

      {/* PII Detection & Encryption Status */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* PII Detections */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.7 }}
        >
          <Card className="p-6 bg-gradient-to-b from-white/5 to-transparent border-white/10 h-full">
            <div className="mb-6">
              <h3 className="text-xl font-semibold text-white mb-1">PII Detection</h3>
              <p className="text-white/60 text-sm">Personally Identifiable Information found</p>
            </div>
            <div className="space-y-4">
              {piiDetections.map((item, index) => (
                <div key={index} className="p-4 rounded-lg bg-white/5 border border-white/5">
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-white font-medium">{item.dataset}</p>
                    <Badge variant="outline" className={getSeverityColor(item.risk.toLowerCase())}>
                      {item.risk}
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-white/60">{item.type}</span>
                    <span className="text-white/80">{item.instances} instances</span>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </motion.div>

        {/* Encryption Status */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.8 }}
        >
          <Card className="p-6 bg-gradient-to-b from-white/5 to-transparent border-white/10 h-full">
            <div className="mb-6">
              <h3 className="text-xl font-semibold text-white mb-1">Encryption Status</h3>
              <p className="text-white/60 text-sm">Data protection mechanisms</p>
            </div>
            <div className="space-y-6">
              {encryptionStatus.map((item, index) => (
                <div key={index}>
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      {item.status ? (
                        <CheckCircle2 className="w-5 h-5 text-green-400" />
                      ) : (
                        <XCircle className="w-5 h-5 text-red-400" />
                      )}
                      <span className="text-white">{item.name}</span>
                    </div>
                    <span className="text-white/80 font-semibold">{item.coverage}%</span>
                  </div>
                  <Progress value={item.coverage} className="h-2" />
                </div>
              ))}
            </div>

            <div className="mt-6 p-4 rounded-lg bg-green-500/10 border border-green-500/20">
              <div className="flex items-center gap-2 mb-2">
                <Lock className="w-5 h-5 text-green-400" />
                <p className="text-green-400 font-semibold">Military-Grade Encryption Active</p>
              </div>
              <p className="text-white/60 text-sm">All data is encrypted with AES-256 encryption at rest and TLS 1.3 in transit</p>
            </div>
          </Card>
        </motion.div>
      </div>
    </div>
  );
}
