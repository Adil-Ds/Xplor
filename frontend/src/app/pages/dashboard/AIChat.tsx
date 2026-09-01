import { motion } from "motion/react";
import { Brain, Send, Sparkles, Code, BarChart3, Table } from "lucide-react";
import { Card } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Badge } from "../../components/ui/badge";
import { useState } from "react";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";

const chartData = [
  { id: "chart-0", month: "Jan", value: 4000 },
  { id: "chart-1", month: "Feb", value: 3000 },
  { id: "chart-2", month: "Mar", value: 5000 },
  { id: "chart-3", month: "Apr", value: 4500 },
  { id: "chart-4", month: "May", value: 6000 },
  { id: "chart-5", month: "Jun", value: 5500 },
];

const promptSuggestions = [
  "Show average salary by department",
  "Detect anomalies in sales data",
  "Predict next quarter revenue",
  "Find duplicate customer records",
];

const chatHistory = [
  {
    role: "user",
    content: "Show me average salary by department",
    time: "2:45 PM"
  },
  {
    role: "assistant",
    content: "I've analyzed your employee data and calculated the average salary by department. Here are the results:",
    time: "2:45 PM",
    chart: true,
    sql: "SELECT department, AVG(salary) as avg_salary FROM employees GROUP BY department ORDER BY avg_salary DESC"
  },
];

export default function AIChat() {
  const [message, setMessage] = useState("");
  const [isTyping, setIsTyping] = useState(false);

  const handleSend = () => {
    if (message.trim()) {
      setMessage("");
      setIsTyping(true);
      setTimeout(() => setIsTyping(false), 2000);
    }
  };

  return (
    <div className="h-[calc(100vh-12rem)] flex flex-col">
      <div className="mb-6">
        <h1 className="text-4xl font-bold text-white mb-2">AI Chat Assistant</h1>
        <p className="text-white/60">Ask questions in natural language, get instant insights</p>
      </div>

      <div className="flex-1 flex gap-6 min-h-0">
        {/* Chat Area */}
        <div className="flex-1 flex flex-col min-w-0">
          <Card className="flex-1 flex flex-col bg-gradient-to-b from-white/5 to-transparent border-white/10 overflow-hidden">
            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              {/* Welcome Message */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="text-center py-8"
              >
                <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-500/20 to-purple-500/20 flex items-center justify-center mx-auto mb-4">
                  <Brain className="w-8 h-8 text-blue-400" />
                </div>
                <h3 className="text-2xl font-semibold text-white mb-2">How can I help you today?</h3>
                <p className="text-white/60">Ask me anything about your data in plain English</p>
              </motion.div>

              {/* Chat Messages */}
              {chatHistory.map((msg, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.1 }}
                  className={`flex gap-4 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  {msg.role === "assistant" && (
                    <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center flex-shrink-0">
                      <Brain className="w-5 h-5 text-white" />
                    </div>
                  )}

                  <div className={`max-w-2xl ${msg.role === "user" ? "order-first" : ""}`}>
                    <div className={`rounded-2xl p-4 ${
                      msg.role === "user" 
                        ? "bg-gradient-to-r from-blue-500 to-purple-600 text-white ml-auto" 
                        : "bg-white/5 border border-white/10 text-white"
                    }`}>
                      <p>{msg.content}</p>
                    </div>

                    {msg.chart && (
                      <div className="mt-4 p-4 rounded-xl bg-white/5 border border-white/10">
                        <ResponsiveContainer width="100%" height={200}>
                          <AreaChart data={chartData} id="ai-chat-response-chart">
                            <defs>
                              <linearGradient id="colorChart-aichat" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.3}/>
                                <stop offset="95%" stopColor="#3B82F6" stopOpacity={0}/>
                              </linearGradient>
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                            <XAxis dataKey="month" stroke="rgba(255,255,255,0.4)" />
                            <YAxis stroke="rgba(255,255,255,0.4)" />
                            <Tooltip
                              contentStyle={{
                                backgroundColor: "rgba(15, 23, 42, 0.95)",
                                border: "1px solid rgba(255,255,255,0.1)",
                                borderRadius: "8px"
                              }}
                            />
                            <Area type="monotone" dataKey="value" stroke="#3B82F6" fill="url(#colorChart-aichat)" strokeWidth={2} name="Value" />
                          </AreaChart>
                        </ResponsiveContainer>
                      </div>
                    )}

                    {msg.sql && (
                      <div className="mt-4 p-4 rounded-xl bg-black/20 border border-white/10">
                        <div className="flex items-center gap-2 mb-2">
                          <Code className="w-4 h-4 text-blue-400" />
                          <span className="text-sm text-blue-400 font-semibold">Generated SQL</span>
                        </div>
                        <code className="text-sm text-white/80 font-mono">{msg.sql}</code>
                      </div>
                    )}

                    <p className="text-xs text-white/40 mt-2 px-2">{msg.time}</p>
                  </div>

                  {msg.role === "user" && (
                    <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-green-500 to-emerald-600 flex items-center justify-center flex-shrink-0 text-white font-semibold">
                      JD
                    </div>
                  )}
                </motion.div>
              ))}

              {/* Typing Indicator */}
              {isTyping && (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex gap-4"
                >
                  <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center flex-shrink-0">
                    <Brain className="w-5 h-5 text-white" />
                  </div>
                  <div className="rounded-2xl p-4 bg-white/5 border border-white/10">
                    <div className="flex gap-2">
                      <div className="w-2 h-2 rounded-full bg-white/60 animate-bounce" />
                      <div className="w-2 h-2 rounded-full bg-white/60 animate-bounce delay-100" />
                      <div className="w-2 h-2 rounded-full bg-white/60 animate-bounce delay-200" />
                    </div>
                  </div>
                </motion.div>
              )}
            </div>

            {/* Input Area */}
            <div className="p-6 border-t border-white/10">
              <div className="flex gap-3">
                <Input
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSend()}
                  placeholder="Ask me anything about your data..."
                  className="flex-1 bg-white/5 border-white/10 text-white placeholder:text-white/40 focus:border-blue-500"
                />
                <Button 
                  onClick={handleSend}
                  className="bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white"
                >
                  <Send className="w-4 h-4" />
                </Button>
              </div>
            </div>
          </Card>
        </div>

        {/* Sidebar */}
        <div className="w-80 flex flex-col gap-6">
          {/* Prompt Suggestions */}
          <Card className="p-6 bg-gradient-to-b from-white/5 to-transparent border-white/10">
            <div className="flex items-center gap-2 mb-4">
              <Sparkles className="w-5 h-5 text-yellow-400" />
              <h3 className="font-semibold text-white">Suggested Prompts</h3>
            </div>
            <div className="space-y-2">
              {promptSuggestions.map((prompt, index) => (
                <button
                  key={index}
                  onClick={() => setMessage(prompt)}
                  className="w-full text-left p-3 rounded-lg bg-white/5 hover:bg-white/10 border border-white/5 hover:border-blue-500/30 text-white/80 hover:text-white text-sm transition-all"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </Card>

          {/* Quick Actions */}
          <Card className="p-6 bg-gradient-to-b from-white/5 to-transparent border-white/10">
            <h3 className="font-semibold text-white mb-4">Quick Actions</h3>
            <div className="space-y-2">
              <Button variant="outline" className="w-full justify-start border-white/10 bg-white/5 text-white hover:bg-white/10">
                <BarChart3 className="w-4 h-4 mr-2" />
                Generate Chart
              </Button>
              <Button variant="outline" className="w-full justify-start border-white/10 bg-white/5 text-white hover:bg-white/10">
                <Table className="w-4 h-4 mr-2" />
                Show Data Table
              </Button>
              <Button variant="outline" className="w-full justify-start border-white/10 bg-white/5 text-white hover:bg-white/10">
                <Code className="w-4 h-4 mr-2" />
                Export SQL
              </Button>
            </div>
          </Card>

          {/* AI Stats */}
          <Card className="p-6 bg-gradient-to-b from-white/5 to-transparent border-white/10">
            <h3 className="font-semibold text-white mb-4">Session Stats</h3>
            <div className="space-y-4">
              <div>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-white/60 text-sm">Queries Today</span>
                  <span className="text-white font-semibold">23</span>
                </div>
              </div>
              <div>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-white/60 text-sm">Avg Response Time</span>
                  <span className="text-white font-semibold">0.8s</span>
                </div>
              </div>
              <div>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-white/60 text-sm">Accuracy Rate</span>
                  <Badge className="bg-green-500/10 text-green-400 border-green-500/20">
                    99.2%
                  </Badge>
                </div>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
