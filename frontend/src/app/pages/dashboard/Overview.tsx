import { motion } from "motion/react";
import { 
  Shield, 
  Brain, 
  TrendingUp, 
  AlertTriangle, 
  Database,
  Activity,
  Zap,
  Clock,
  ArrowUp,
  ArrowDown,
  CheckCircle2
} from "lucide-react";
import { Card } from "../../components/ui/card";
import { Progress } from "../../components/ui/progress";
import { LineChart, Line, AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";

const kpiData = [
  { id: "kpi-dataset-health", icon: Database, label: "Dataset Health", value: "96.8%", trend: "+4.2%", trendUp: true, color: "from-blue-500 to-cyan-500" },
  { id: "kpi-security-score", icon: Shield, label: "Security Score", value: "98.5", trend: "+12%", trendUp: true, color: "from-green-500 to-emerald-500" },
  { id: "kpi-ai-confidence", icon: Brain, label: "AI Confidence", value: "99.2%", trend: "+2.1%", trendUp: true, color: "from-purple-500 to-pink-500" },
  { id: "kpi-active-threats", icon: AlertTriangle, label: "Active Threats", value: "3", trend: "-8", trendUp: true, color: "from-red-500 to-orange-500" },
  { id: "kpi-forecast-accuracy", icon: Activity, label: "Forecast Accuracy", value: "94.7%", trend: "+6.3%", trendUp: true, color: "from-yellow-500 to-orange-500" },
  { id: "kpi-processing-speed", icon: Zap, label: "Processing Speed", value: "2.4s", trend: "-0.6s", trendUp: true, color: "from-cyan-500 to-blue-500" },
];

const timeSeriesData = [
  { id: "ts-0", date: "Mon", value: 85, predicted: 87 },
  { id: "ts-1", date: "Tue", value: 92, predicted: 90 },
  { id: "ts-2", date: "Wed", value: 88, predicted: 89 },
  { id: "ts-3", date: "Thu", value: 95, predicted: 94 },
  { id: "ts-4", date: "Fri", value: 91, predicted: 93 },
  { id: "ts-5", date: "Sat", value: 97, predicted: 96 },
  { id: "ts-6", date: "Sun", value: 94, predicted: 95 },
];

const threatData = [
  { id: "threat-0", name: "Low", value: 45, color: "#10B981" },
  { id: "threat-1", name: "Medium", value: 30, color: "#F59E0B" },
  { id: "threat-2", name: "High", value: 20, color: "#EF4444" },
  { id: "threat-3", name: "Critical", value: 5, color: "#DC2626" },
];

const departmentData = [
  { id: "dept-0", department: "Sales", risk: 85, data: 120 },
  { id: "dept-1", department: "Marketing", risk: 72, data: 95 },
  { id: "dept-2", department: "Finance", risk: 91, data: 140 },
  { id: "dept-3", department: "HR", risk: 68, data: 78 },
  { id: "dept-4", department: "IT", risk: 95, data: 165 },
];

const recentActivities = [
  { id: "activity-0", icon: CheckCircle2, text: "Dataset 'Q1_Sales_2024' processed successfully", time: "2 min ago", color: "text-green-400" },
  { id: "activity-1", icon: AlertTriangle, text: "3 PII instances detected in 'Customer_Data'", time: "5 min ago", color: "text-yellow-400" },
  { id: "activity-2", icon: Brain, text: "AI model training completed with 99.2% accuracy", time: "12 min ago", color: "text-blue-400" },
  { id: "activity-3", icon: Shield, text: "Security scan completed - no threats found", time: "18 min ago", color: "text-green-400" },
];

export default function Overview() {
  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-4xl font-bold text-white mb-2">Dashboard Overview</h1>
        <p className="text-white/60">Welcome back! Here's what's happening with your data today.</p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {kpiData.map((kpi, index) => (
          <motion.div
            key={kpi.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
          >
            <Card className="p-6 bg-gradient-to-b from-white/5 to-transparent border-white/10 hover:border-white/20 transition-all relative overflow-hidden group">
              <div className={`absolute top-0 right-0 w-32 h-32 bg-gradient-to-br ${kpi.color} opacity-10 blur-3xl group-hover:opacity-20 transition-opacity`} />
              
              <div className="relative">
                <div className="flex items-center justify-between mb-4">
                  <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${kpi.color} flex items-center justify-center`}>
                    <kpi.icon className="w-6 h-6 text-white" />
                  </div>
                  <div className={`flex items-center gap-1 text-sm ${kpi.trendUp ? "text-green-400" : "text-red-400"}`}>
                    {kpi.trendUp ? <ArrowUp className="w-4 h-4" /> : <ArrowDown className="w-4 h-4" />}
                    <span>{kpi.trend}</span>
                  </div>
                </div>

                <div className="space-y-1">
                  <p className="text-white/60 text-sm">{kpi.label}</p>
                  <p className="text-3xl font-bold text-white">{kpi.value}</p>
                </div>
              </div>
            </Card>
          </motion.div>
        ))}
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Time Series Chart */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.3 }}
        >
          <Card className="p-6 bg-gradient-to-b from-white/5 to-transparent border-white/10">
            <div className="mb-6">
              <h3 className="text-xl font-semibold text-white mb-1">Security Score Trend</h3>
              <p className="text-white/60 text-sm">Actual vs Predicted performance</p>
            </div>
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={timeSeriesData} id="security-score-chart">
                <defs>
                  <linearGradient id="colorValue-overview" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#3B82F6" stopOpacity={0}/>
                  </linearGradient>
                  <linearGradient id="colorPredicted-overview" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#8B5CF6" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#8B5CF6" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="date" stroke="rgba(255,255,255,0.4)" />
                <YAxis stroke="rgba(255,255,255,0.4)" />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "rgba(15, 23, 42, 0.95)",
                    border: "1px solid rgba(255,255,255,0.1)",
                    borderRadius: "8px",
                    color: "#fff"
                  }}
                />
                <Area type="monotone" dataKey="value" stroke="#3B82F6" fill="url(#colorValue-overview)" strokeWidth={2} name="Actual" />
                <Area type="monotone" dataKey="predicted" stroke="#8B5CF6" fill="url(#colorPredicted-overview)" strokeWidth={2} strokeDasharray="5 5" name="Predicted" />
              </AreaChart>
            </ResponsiveContainer>
          </Card>
        </motion.div>

        {/* Threat Distribution */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.4 }}
        >
          <Card className="p-6 bg-gradient-to-b from-white/5 to-transparent border-white/10">
            <div className="mb-6">
              <h3 className="text-xl font-semibold text-white mb-1">Threat Distribution</h3>
              <p className="text-white/60 text-sm">Current security threats by severity</p>
            </div>
            <div className="flex items-center">
              <ResponsiveContainer width="60%" height={250}>
                <PieChart id="threat-distribution-chart">
                  <Pie
                    data={threatData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={90}
                    paddingAngle={5}
                    dataKey="value"
                    nameKey="name"
                  >
                    {threatData.map((entry, index) => (
                      <Cell key={`threat-cell-${entry.id}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "rgba(15, 23, 42, 0.95)",
                      border: "1px solid rgba(255,255,255,0.1)",
                      borderRadius: "8px",
                      color: "#fff"
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
              <div className="flex-1 space-y-3">
                {threatData.map((item) => (
                  <div key={item.id} className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded-full" style={{ backgroundColor: item.color }} />
                      <span className="text-white/80 text-sm">{item.name}</span>
                    </div>
                    <span className="text-white font-semibold">{item.value}%</span>
                  </div>
                ))}
              </div>
            </div>
          </Card>
        </motion.div>
      </div>

      {/* Department Performance */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5 }}
      >
        <Card className="p-6 bg-gradient-to-b from-white/5 to-transparent border-white/10">
          <div className="mb-6">
            <h3 className="text-xl font-semibold text-white mb-1">Department Analytics</h3>
            <p className="text-white/60 text-sm">Risk scores and data volume by department</p>
          </div>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={departmentData} id="department-analytics-chart">
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="department" stroke="rgba(255,255,255,0.4)" />
              <YAxis stroke="rgba(255,255,255,0.4)" />
              <Tooltip
                contentStyle={{
                  backgroundColor: "rgba(15, 23, 42, 0.95)",
                  border: "1px solid rgba(255,255,255,0.1)",
                  borderRadius: "8px",
                  color: "#fff"
                }}
              />
              <Legend />
              <Bar dataKey="risk" fill="#3B82F6" radius={[8, 8, 0, 0]} name="Risk Score" id="bar-risk" />
              <Bar dataKey="data" fill="#8B5CF6" radius={[8, 8, 0, 0]} name="Data Volume (GB)" id="bar-data" />
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </motion.div>

      {/* Recent Activity & Quick Actions */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Activity */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.6 }}
        >
          <Card className="p-6 bg-gradient-to-b from-white/5 to-transparent border-white/10">
            <div className="mb-6">
              <h3 className="text-xl font-semibold text-white mb-1">Recent Activity</h3>
              <p className="text-white/60 text-sm">Latest updates from your workspace</p>
            </div>
            <div className="space-y-4">
              {recentActivities.map((activity, index) => (
                <motion.div
                  key={activity.id}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.7 + index * 0.1 }}
                  className="flex items-start gap-3 p-3 rounded-lg bg-white/5 hover:bg-white/10 transition-colors"
                >
                  <div className={`w-8 h-8 rounded-lg bg-white/5 flex items-center justify-center flex-shrink-0`}>
                    <activity.icon className={`w-4 h-4 ${activity.color}`} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-white/80 text-sm">{activity.text}</p>
                    <div className="flex items-center gap-2 mt-1">
                      <Clock className="w-3 h-3 text-white/40" />
                      <span className="text-xs text-white/40">{activity.time}</span>
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          </Card>
        </motion.div>

        {/* AI Processing Status */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.6 }}
        >
          <Card className="p-6 bg-gradient-to-b from-white/5 to-transparent border-white/10">
            <div className="mb-6">
              <h3 className="text-xl font-semibold text-white mb-1">AI Processing Status</h3>
              <p className="text-white/60 text-sm">Current pipeline operations</p>
            </div>
            <div className="space-y-6">
              {[
                { id: "pipeline-data-cleaning", task: "Data Cleaning", progress: 100, status: "Complete" },
                { id: "pipeline-anomaly-detection", task: "Anomaly Detection", progress: 78, status: "Processing" },
                { id: "pipeline-risk-analysis", task: "Risk Analysis", progress: 45, status: "Processing" },
                { id: "pipeline-forecasting-model", task: "Forecasting Model", progress: 23, status: "Processing" },
              ].map((item) => (
                <div key={item.id}>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-white/80 text-sm">{item.task}</span>
                    <span className={`text-xs px-2 py-1 rounded-full ${
                      item.progress === 100 
                        ? "bg-green-500/10 text-green-400" 
                        : "bg-blue-500/10 text-blue-400"
                    }`}>
                      {item.status}
                    </span>
                  </div>
                  <Progress value={item.progress} className="h-2" />
                  <div className="text-xs text-white/40 mt-1">{item.progress}%</div>
                </div>
              ))}
            </div>
          </Card>
        </motion.div>
      </div>
    </div>
  );
}
