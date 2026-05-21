import { motion } from "motion/react";
import { TrendingUp, Calendar, Target } from "lucide-react";
import { Card } from "../../components/ui/card";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";

const forecastData = [
  { id: "forecast-0", month: "Jul", actual: 6500, predicted: 6400, lower: 6100, upper: 6700 },
  { id: "forecast-1", month: "Aug", predicted: 7200, lower: 6800, upper: 7600 },
  { id: "forecast-2", month: "Sep", predicted: 7800, lower: 7300, upper: 8300 },
  { id: "forecast-3", month: "Oct", predicted: 8100, lower: 7600, upper: 8600 },
];

export default function Forecasting() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-4xl font-bold text-white mb-2">AI Forecasting</h1>
        <p className="text-white/60">Predictive analytics and future trend analysis</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {[
          { icon: TrendingUp, label: "Next Quarter Prediction", value: "$245K", color: "from-green-500 to-emerald-500" },
          { icon: Target, label: "Confidence Level", value: "94.7%", color: "from-blue-500 to-cyan-500" },
          { icon: Calendar, label: "Forecast Period", value: "90 Days", color: "from-purple-500 to-pink-500" },
        ].map((item, index) => (
          <motion.div key={index} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: index * 0.1 }}>
            <Card className="p-6 bg-gradient-to-b from-white/5 to-transparent border-white/10">
              <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${item.color} flex items-center justify-center mb-4`}>
                <item.icon className="w-6 h-6 text-white" />
              </div>
              <p className="text-white/60 text-sm">{item.label}</p>
              <p className="text-3xl font-bold text-white">{item.value}</p>
            </Card>
          </motion.div>
        ))}
      </div>

      <Card className="p-6 bg-gradient-to-b from-white/5 to-transparent border-white/10">
        <h3 className="text-xl font-semibold text-white mb-6">Revenue Forecast</h3>
        <ResponsiveContainer width="100%" height={400}>
          <LineChart data={forecastData} id="revenue-forecast-chart">
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis dataKey="month" stroke="rgba(255,255,255,0.4)" />
            <YAxis stroke="rgba(255,255,255,0.4)" />
            <Tooltip contentStyle={{ backgroundColor: "rgba(15, 23, 42, 0.95)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px" }} />
            <Legend />
            <Line type="monotone" dataKey="actual" stroke="#10B981" strokeWidth={3} dot={{ r: 6 }} name="Actual" id="line-actual" />
            <Line type="monotone" dataKey="predicted" stroke="#3B82F6" strokeWidth={3} strokeDasharray="5 5" dot={{ r: 6 }} name="Predicted" id="line-predicted" />
            <Line type="monotone" dataKey="lower" stroke="#8B5CF6" strokeWidth={1} strokeDasharray="3 3" dot={false} name="Lower Bound" id="line-lower" />
            <Line type="monotone" dataKey="upper" stroke="#8B5CF6" strokeWidth={1} strokeDasharray="3 3" dot={false} name="Upper Bound" id="line-upper" />
          </LineChart>
        </ResponsiveContainer>
      </Card>
    </div>
  );
}
