import { motion } from "motion/react";
import { BarChart3, TrendingUp, LineChart as LineChartIcon, Activity } from "lucide-react";
import { Card } from "../../components/ui/card";
import { LineChart, Line, BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, AreaChart, Area, ScatterChart as RechartsScatterChart, Scatter } from "recharts";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../../components/ui/select";
import { useState, useMemo, useCallback } from "react";

const salesData = [
  { id: "month-0", month: "Jan", sales: 4000, revenue: 2400, profit: 1600, customers: 320, growth: 12 },
  { id: "month-1", month: "Feb", sales: 3000, revenue: 1398, profit: 1000, customers: 280, growth: 8 },
  { id: "month-2", month: "Mar", sales: 5000, revenue: 9800, profit: 2900, customers: 450, growth: 18 },
  { id: "month-3", month: "Apr", sales: 2780, revenue: 3908, profit: 2000, customers: 310, growth: 10 },
  { id: "month-4", month: "May", sales: 4890, revenue: 4800, profit: 2500, customers: 420, growth: 15 },
  { id: "month-5", month: "Jun", sales: 6390, revenue: 3800, profit: 3100, customers: 520, growth: 22 },
];

const categoryData = [
  { id: "cat-0", name: "Electronics", value: 4500, color: "#3B82F6" },
  { id: "cat-1", name: "Clothing", value: 3200, color: "#8B5CF6" },
  { id: "cat-2", name: "Food", value: 2800, color: "#10B981" },
  { id: "cat-3", name: "Books", value: 1500, color: "#F59E0B" },
];

const chartTypes = [
  { value: "bar", label: "Bar Chart", icon: BarChart3 },
  { value: "line", label: "Line Chart", icon: LineChartIcon },
  { value: "area", label: "Area Chart", icon: TrendingUp },
  { value: "scatter", label: "Scatter Plot", icon: Activity },
];

const dataFeatures = [
  { value: "sales", label: "Sales", color: "#3B82F6" },
  { value: "revenue", label: "Revenue", color: "#8B5CF6" },
  { value: "profit", label: "Profit", color: "#10B981" },
  { value: "customers", label: "Customers", color: "#F59E0B" },
  { value: "growth", label: "Growth %", color: "#EC4899" },
];

export default function Analytics() {
  const [selectedChartType, setSelectedChartType] = useState("bar");
  const [selectedFeature1, setSelectedFeature1] = useState("sales");
  const [selectedFeature2, setSelectedFeature2] = useState("revenue");

  const getFeatureColor = useCallback((feature: string) => {
    return dataFeatures.find(f => f.value === feature)?.color || "#3B82F6";
  }, []);

  const getFeatureLabel = useCallback((feature: string) => {
    return dataFeatures.find(f => f.value === feature)?.label || feature;
  }, []);

  const customChart = useMemo(() => {
    const tooltipStyle = { backgroundColor: "rgba(15, 23, 42, 0.95)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px" };

    switch (selectedChartType) {
      case "line":
        return (
          <LineChart data={salesData} id={`line-chart-${selectedFeature1}-${selectedFeature2}`}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis dataKey="month" stroke="rgba(255,255,255,0.4)" />
            <YAxis stroke="rgba(255,255,255,0.4)" />
            <Tooltip contentStyle={tooltipStyle} />
            <Legend />
            <Line type="monotone" dataKey={selectedFeature1} stroke={getFeatureColor(selectedFeature1)} strokeWidth={3} name={getFeatureLabel(selectedFeature1)} id={`line-${selectedFeature1}`} />
            <Line type="monotone" dataKey={selectedFeature2} stroke={getFeatureColor(selectedFeature2)} strokeWidth={3} name={getFeatureLabel(selectedFeature2)} id={`line-${selectedFeature2}`} />
          </LineChart>
        );

      case "area":
        return (
          <AreaChart data={salesData} id={`area-chart-${selectedFeature1}-${selectedFeature2}`}>
            <defs>
              <linearGradient id={`colorFeature1-${selectedFeature1}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={getFeatureColor(selectedFeature1)} stopOpacity={0.3}/>
                <stop offset="95%" stopColor={getFeatureColor(selectedFeature1)} stopOpacity={0}/>
              </linearGradient>
              <linearGradient id={`colorFeature2-${selectedFeature2}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={getFeatureColor(selectedFeature2)} stopOpacity={0.3}/>
                <stop offset="95%" stopColor={getFeatureColor(selectedFeature2)} stopOpacity={0}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis dataKey="month" stroke="rgba(255,255,255,0.4)" />
            <YAxis stroke="rgba(255,255,255,0.4)" />
            <Tooltip contentStyle={tooltipStyle} />
            <Legend />
            <Area type="monotone" dataKey={selectedFeature1} stroke={getFeatureColor(selectedFeature1)} fill={`url(#colorFeature1-${selectedFeature1})`} strokeWidth={2} name={getFeatureLabel(selectedFeature1)} id={`area-${selectedFeature1}`} />
            <Area type="monotone" dataKey={selectedFeature2} stroke={getFeatureColor(selectedFeature2)} fill={`url(#colorFeature2-${selectedFeature2})`} strokeWidth={2} name={getFeatureLabel(selectedFeature2)} id={`area-${selectedFeature2}`} />
          </AreaChart>
        );

      case "scatter": {
        const scatterData = salesData.map(item => ({
          x: item[selectedFeature1 as keyof typeof item] as number,
          y: item[selectedFeature2 as keyof typeof item] as number,
          month: item.month
        }));
        return (
          <RechartsScatterChart data={salesData} id={`scatter-chart-${selectedFeature1}-${selectedFeature2}`}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis type="number" dataKey="x" name={getFeatureLabel(selectedFeature1)} stroke="rgba(255,255,255,0.4)" />
            <YAxis type="number" dataKey="y" name={getFeatureLabel(selectedFeature2)} stroke="rgba(255,255,255,0.4)" />
            <Tooltip contentStyle={tooltipStyle} />
            <Scatter name="Data Points" data={scatterData} fill={getFeatureColor(selectedFeature1)} id={`scatter-${selectedFeature1}-${selectedFeature2}`} />
          </RechartsScatterChart>
        );
      }
      default: // bar
        return (
          <BarChart data={salesData} id={`bar-chart-${selectedFeature1}-${selectedFeature2}`}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis dataKey="month" stroke="rgba(255,255,255,0.4)" />
            <YAxis stroke="rgba(255,255,255,0.4)" />
            <Tooltip contentStyle={tooltipStyle} />
            <Legend />
            <Bar dataKey={selectedFeature1} fill={getFeatureColor(selectedFeature1)} radius={[8, 8, 0, 0]} name={getFeatureLabel(selectedFeature1)} id={`bar-${selectedFeature1}`} />
            <Bar dataKey={selectedFeature2} fill={getFeatureColor(selectedFeature2)} radius={[8, 8, 0, 0]} name={getFeatureLabel(selectedFeature2)} id={`bar-${selectedFeature2}`} />
          </BarChart>
        );
    }
  }, [selectedChartType, selectedFeature1, selectedFeature2, getFeatureColor, getFeatureLabel]);

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-4xl font-bold text-white mb-2">Analytics Dashboard</h1>
          <p className="text-white/60">Advanced data visualization and insights</p>
        </div>

        <div className="flex items-center gap-4">
          <div className="flex flex-col gap-2">
            <label className="text-xs text-white/60">Chart Type</label>
            <Select value={selectedChartType} onValueChange={setSelectedChartType}>
              <SelectTrigger className="w-[180px] bg-white/5 border-white/10 text-white">
                <SelectValue placeholder="Select chart type" />
              </SelectTrigger>
              <SelectContent className="bg-[#0F172A] border-white/10">
                {chartTypes.map((type) => (
                  <SelectItem key={type.value} value={type.value} className="text-white hover:bg-white/10 focus:bg-white/10">
                    <div className="flex items-center gap-2">
                      <type.icon className="w-4 h-4" />
                      {type.label}
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="flex flex-col gap-2">
            <label className="text-xs text-white/60">Feature 1</label>
            <Select value={selectedFeature1} onValueChange={setSelectedFeature1}>
              <SelectTrigger className="w-[180px] bg-white/5 border-white/10 text-white">
                <SelectValue placeholder="Select feature" />
              </SelectTrigger>
              <SelectContent className="bg-[#0F172A] border-white/10">
                {dataFeatures.map((feature) => (
                  <SelectItem key={feature.value} value={feature.value} className="text-white hover:bg-white/10 focus:bg-white/10">
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded-full" style={{ backgroundColor: feature.color }} />
                      {feature.label}
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="flex flex-col gap-2">
            <label className="text-xs text-white/60">Feature 2</label>
            <Select value={selectedFeature2} onValueChange={setSelectedFeature2}>
              <SelectTrigger className="w-[180px] bg-white/5 border-white/10 text-white">
                <SelectValue placeholder="Select feature" />
              </SelectTrigger>
              <SelectContent className="bg-[#0F172A] border-white/10">
                {dataFeatures.map((feature) => (
                  <SelectItem key={feature.value} value={feature.value} className="text-white hover:bg-white/10 focus:bg-white/10">
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded-full" style={{ backgroundColor: feature.color }} />
                      {feature.label}
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      </div>

      {/* Top Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {[
          { label: "Total Revenue", value: "$124,563", change: "+12.5%", color: "from-green-500 to-emerald-500" },
          { label: "Total Sales", value: "26,060", change: "+8.2%", color: "from-blue-500 to-cyan-500" },
          { label: "Avg Profit Margin", value: "42.3%", change: "+3.1%", color: "from-purple-500 to-pink-500" },
        ].map((metric, index) => (
          <motion.div
            key={index}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
          >
            <Card className="p-6 bg-gradient-to-b from-white/5 to-transparent border-white/10">
              <p className="text-white/60 text-sm mb-2">{metric.label}</p>
              <p className="text-3xl font-bold text-white mb-2">{metric.value}</p>
              <div className={`text-sm font-semibold bg-gradient-to-r ${metric.color} bg-clip-text text-transparent`}>
                {metric.change} vs last month
              </div>
            </Card>
          </motion.div>
        ))}
      </div>

      {/* Custom Interactive Chart */}
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.3 }}>
        <Card className="p-6 bg-gradient-to-b from-white/5 to-transparent border-white/10">
          <h3 className="text-xl font-semibold text-white mb-6">Custom Data Comparison</h3>
          <ResponsiveContainer width="100%" height={400}>
            {customChart}
          </ResponsiveContainer>
        </Card>
      </motion.div>

      {/* Static Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.4 }}>
          <Card className="p-6 bg-gradient-to-b from-white/5 to-transparent border-white/10">
            <h3 className="text-xl font-semibold text-white mb-6">Category Distribution</h3>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart id="category-distribution-chart">
                <Pie data={categoryData} cx="50%" cy="50%" labelLine={false} outerRadius={100} dataKey="value" nameKey="name">
                  {categoryData.map((entry, index) => (
                    <Cell key={`category-cell-${entry.name}-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ backgroundColor: "rgba(15, 23, 42, 0.95)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px" }} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </Card>
        </motion.div>

        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.5 }}>
          <Card className="p-6 bg-gradient-to-b from-white/5 to-transparent border-white/10">
            <h3 className="text-xl font-semibold text-white mb-6">All Metrics Overview</h3>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={salesData} id="all-metrics-chart">
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="month" stroke="rgba(255,255,255,0.4)" />
                <YAxis stroke="rgba(255,255,255,0.4)" />
                <Tooltip contentStyle={{ backgroundColor: "rgba(15, 23, 42, 0.95)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px" }} />
                <Legend />
                <Bar dataKey="sales" fill="#3B82F6" radius={[4, 4, 0, 0]} name="Sales" id="bar-sales-all" />
                <Bar dataKey="revenue" fill="#8B5CF6" radius={[4, 4, 0, 0]} name="Revenue" id="bar-revenue-all" />
                <Bar dataKey="profit" fill="#10B981" radius={[4, 4, 0, 0]} name="Profit" id="bar-profit-all" />
              </BarChart>
            </ResponsiveContainer>
          </Card>
        </motion.div>
      </div>
    </div>
  );
}
