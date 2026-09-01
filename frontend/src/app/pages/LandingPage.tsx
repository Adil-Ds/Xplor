import { motion } from "motion/react";
import { Link } from "react-router";
import { 
  ArrowRight, 
  Brain, 
  Shield, 
  TrendingUp, 
  Sparkles, 
  Database, 
  Lock,
  Activity,
  AlertTriangle,
  BarChart3,
  CheckCircle2,
  Eye,
  Zap,
  Users,
  Globe,
  MessageSquare
} from "lucide-react";
import { Button } from "../components/ui/button";
import { Card } from "../components/ui/card";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-background overflow-hidden">
      {/* Animated background */}
      <div className="fixed inset-0 -z-10">
        <div className="absolute inset-0 bg-gradient-to-b from-[#070B14] via-[#0F172A] to-[#070B14]" />
        <div className="absolute inset-0 opacity-20">
          <div className="absolute top-0 left-1/4 w-96 h-96 bg-blue-500 rounded-full mix-blend-multiply filter blur-3xl animate-pulse" />
          <div className="absolute top-1/3 right-1/4 w-96 h-96 bg-purple-500 rounded-full mix-blend-multiply filter blur-3xl animate-pulse delay-1000" />
          <div className="absolute bottom-1/4 left-1/2 w-96 h-96 bg-cyan-500 rounded-full mix-blend-multiply filter blur-3xl animate-pulse delay-500" />
        </div>
        {/* Grid pattern */}
        <div className="absolute inset-0" style={{
          backgroundImage: `linear-gradient(rgba(59, 130, 246, 0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(59, 130, 246, 0.1) 1px, transparent 1px)`,
          backgroundSize: '50px 50px'
        }} />
      </div>

      {/* Navigation */}
      <nav className="sticky top-0 z-50 backdrop-blur-xl bg-[#070B14]/80 border-b border-white/5">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <motion.div 
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              className="flex items-center gap-2"
            >
              <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
                <Brain className="w-6 h-6 text-white" />
              </div>
              <span className="text-xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
                Xplore
              </span>
            </motion.div>
            
            <div className="hidden md:flex items-center gap-8">
              <a href="#features" className="text-white/80 hover:text-white transition-colors">Features</a>
              <a href="#demo" className="text-white/80 hover:text-white transition-colors">Demo</a>
              <a href="#solutions" className="text-white/80 hover:text-white transition-colors">Solutions</a>
              <a href="#about" className="text-white/80 hover:text-white transition-colors">About</a>
            </div>

            <div className="flex items-center gap-4">
              <Link to="/login">
                <Button variant="ghost" className="text-white/80 hover:text-white">
                  Login
                </Button>
              </Link>
              <Link to="/signup">
                <Button className="bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white">
                  Get Started
                  <ArrowRight className="ml-2 w-4 h-4" />
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative py-32 px-6">
        <div className="max-w-7xl mx-auto">
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            className="text-center"
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.2 }}
              className="inline-block mb-6"
            >
              <div className="px-6 py-2 rounded-full bg-gradient-to-r from-blue-500/10 to-purple-500/10 border border-blue-500/20 backdrop-blur-sm">
                <span className="text-sm text-blue-400 flex items-center gap-2">
                  <Sparkles className="w-4 h-4" />
                  Enterprise-Grade AI Security Analytics
                </span>
              </div>
            </motion.div>

            <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold mb-8 bg-gradient-to-r from-white via-blue-100 to-purple-200 bg-clip-text text-transparent leading-tight">
              AI That Understands,<br />
              Cleans & Protects<br />
              Your Data
            </h1>

            <p className="text-xl md:text-2xl text-white/60 max-w-3xl mx-auto mb-8 leading-relaxed">
              Enterprise-grade AI analytics platform with automated security intelligence,
              anomaly detection, forecasting, and natural language querying.
            </p>

            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Link to="/signup">
                <Button size="lg" className="bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white px-8 py-6 text-lg shadow-lg shadow-blue-500/30 hover:shadow-blue-500/50 transition-all">
                  Get Started Free
                  <ArrowRight className="ml-2 w-5 h-5" />
                </Button>
              </Link>
              <Button size="lg" variant="outline" className="border-white/20 text-white hover:bg-white/5 px-8 py-6 text-lg backdrop-blur-sm">
                Watch Demo
                <svg className="ml-2 w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </Button>
            </div>

            {/* Floating dashboard preview */}
            <motion.div
              initial={{ opacity: 0, y: 40 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.6, duration: 1 }}
              className="mt-20"
            >
              <div className="relative">
                <div className="absolute inset-0 bg-gradient-to-r from-blue-500/20 to-purple-500/20 blur-3xl" />
                <div className="relative rounded-2xl border border-white/10 bg-gradient-to-b from-white/5 to-transparent backdrop-blur-xl p-2 shadow-2xl">
                  <div className="rounded-lg bg-[#070B14]/90 p-8">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      {/* Risk Score */}
                      <motion.div
                        animate={{ 
                          boxShadow: ['0 0 20px rgba(59, 130, 246, 0.3)', '0 0 40px rgba(59, 130, 246, 0.5)', '0 0 20px rgba(59, 130, 246, 0.3)']
                        }}
                        transition={{ duration: 2, repeat: Infinity }}
                        className="bg-gradient-to-br from-blue-500/10 to-purple-500/10 rounded-xl p-6 border border-blue-500/20"
                      >
                        <div className="flex items-center justify-between mb-4">
                          <span className="text-white/60">Security Score</span>
                          <Shield className="w-5 h-5 text-blue-400" />
                        </div>
                        <div className="text-4xl font-bold text-white mb-2">98.5</div>
                        <div className="flex items-center gap-2 text-green-400 text-sm">
                          <TrendingUp className="w-4 h-4" />
                          <span>+12% from last week</span>
                        </div>
                      </motion.div>

                      {/* Active Threats */}
                      <motion.div
                        animate={{ 
                          boxShadow: ['0 0 20px rgba(239, 68, 68, 0.3)', '0 0 40px rgba(239, 68, 68, 0.5)', '0 0 20px rgba(239, 68, 68, 0.3)']
                        }}
                        transition={{ duration: 2, repeat: Infinity, delay: 0.5 }}
                        className="bg-gradient-to-br from-red-500/10 to-orange-500/10 rounded-xl p-6 border border-red-500/20"
                      >
                        <div className="flex items-center justify-between mb-4">
                          <span className="text-white/60">Active Threats</span>
                          <AlertTriangle className="w-5 h-5 text-red-400" />
                        </div>
                        <div className="text-4xl font-bold text-white mb-2">3</div>
                        <div className="flex items-center gap-2 text-red-400 text-sm">
                          <Activity className="w-4 h-4" />
                          <span>2 critical, 1 medium</span>
                        </div>
                      </motion.div>

                      {/* AI Confidence */}
                      <motion.div
                        animate={{ 
                          boxShadow: ['0 0 20px rgba(16, 185, 129, 0.3)', '0 0 40px rgba(16, 185, 129, 0.5)', '0 0 20px rgba(16, 185, 129, 0.3)']
                        }}
                        transition={{ duration: 2, repeat: Infinity, delay: 1 }}
                        className="bg-gradient-to-br from-green-500/10 to-emerald-500/10 rounded-xl p-6 border border-green-500/20"
                      >
                        <div className="flex items-center justify-between mb-4">
                          <span className="text-white/60">AI Confidence</span>
                          <Brain className="w-5 h-5 text-green-400" />
                        </div>
                        <div className="text-4xl font-bold text-white mb-2">99.2%</div>
                        <div className="flex items-center gap-2 text-green-400 text-sm">
                          <CheckCircle2 className="w-4 h-4" />
                          <span>Highly accurate</span>
                        </div>
                      </motion.div>
                    </div>
                  </div>
                </div>
              </div>
            </motion.div>
          </motion.div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="py-32 px-6">
        <div className="max-w-7xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-20"
          >
            <h2 className="text-5xl md:text-6xl font-bold mb-6 bg-gradient-to-r from-white to-white/60 bg-clip-text text-transparent">
              Next-Generation Features
            </h2>
            <p className="text-xl text-white/60 max-w-2xl mx-auto">
              Enterprise-grade AI capabilities that transform how you work with data
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[
              {
                icon: Brain,
                title: "AI Data Cleaning",
                description: "Automatically detect and fix data quality issues with advanced ML algorithms",
                color: "from-blue-500 to-cyan-500"
              },
              {
                icon: MessageSquare,
                title: "Natural Language Querying",
                description: "Ask questions in plain English and get instant insights from your data",
                color: "from-purple-500 to-pink-500"
              },
              {
                icon: Shield,
                title: "Risk Score Engine",
                description: "Real-time security risk assessment with predictive threat detection",
                color: "from-red-500 to-orange-500"
              },
              {
                icon: Eye,
                title: "PII Detection",
                description: "Automatically identify and protect sensitive personal information",
                color: "from-green-500 to-emerald-500"
              },
              {
                icon: TrendingUp,
                title: "Forecasting AI",
                description: "Advanced predictive analytics powered by state-of-the-art ML models",
                color: "from-yellow-500 to-orange-500"
              },
              {
                icon: BarChart3,
                title: "Automated Dashboards",
                description: "Generate beautiful, interactive dashboards from your data instantly",
                color: "from-cyan-500 to-blue-500"
              },
              {
                icon: AlertTriangle,
                title: "Anomaly Detection",
                description: "Real-time monitoring and alerting for unusual patterns and outliers",
                color: "from-pink-500 to-purple-500"
              },
              {
                icon: Lock,
                title: "AES-256 Encryption",
                description: "Military-grade encryption for data at rest and in transit",
                color: "from-indigo-500 to-purple-500"
              },
              {
                icon: Users,
                title: "Role-Based Access",
                description: "Granular permissions and team collaboration features",
                color: "from-teal-500 to-green-500"
              },
            ].map((feature, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.1 }}
                whileHover={{ y: -5 }}
              >
                <Card className="group p-8 bg-gradient-to-b from-white/5 to-transparent border-white/10 hover:border-white/20 transition-all duration-300 h-full">
                  <div className={`w-14 h-14 rounded-xl bg-gradient-to-br ${feature.color} flex items-center justify-center mb-6 group-hover:scale-110 transition-transform`}>
                    <feature.icon className="w-7 h-7 text-white" />
                  </div>
                  <h3 className="text-xl font-semibold text-white mb-3">{feature.title}</h3>
                  <p className="text-white/60 leading-relaxed">{feature.description}</p>
                </Card>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* AI Workflow Section */}
      <section className="py-32 px-6 bg-gradient-to-b from-transparent via-blue-500/5 to-transparent">
        <div className="max-w-7xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-20"
          >
            <h2 className="text-5xl md:text-6xl font-bold mb-6 bg-gradient-to-r from-white to-white/60 bg-clip-text text-transparent">
              Intelligent Workflow
            </h2>
            <p className="text-xl text-white/60 max-w-2xl mx-auto">
              From upload to insights in seconds with our AI-powered pipeline
            </p>
          </motion.div>

          <div className="relative">
            <div className="absolute top-1/2 left-0 right-0 h-0.5 bg-gradient-to-r from-blue-500/0 via-blue-500/50 to-blue-500/0" />

            <div className="grid grid-cols-1 md:grid-cols-6 gap-4 relative">
              {[
                { icon: Database, label: "Upload File" },
                { icon: Brain, label: "AI Processing" },
                { icon: Sparkles, label: "Data Cleaning" },
                { icon: Shield, label: "Risk Analysis" },
                { icon: BarChart3, label: "Dashboard" },
                { icon: Zap, label: "AI Insights" },
              ].map((step, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, scale: 0.8 }}
                  whileInView={{ opacity: 1, scale: 1 }}
                  viewport={{ once: true }}
                  transition={{ delay: index * 0.15 }}
                  className="flex flex-col items-center"
                >
                  <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-blue-500/20 to-purple-500/20 border border-blue-500/30 flex items-center justify-center mb-4 relative z-10 backdrop-blur-xl">
                    <step.icon className="w-10 h-10 text-blue-400" />
                  </div>
                  <span className="text-white/80 text-center">{step.label}</span>
                </motion.div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Solutions Section */}
      <section id="solutions" className="py-32 px-6">
        <div className="max-w-7xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-20"
          >
            <h2 className="text-5xl md:text-6xl font-bold mb-6 bg-gradient-to-r from-white to-white/60 bg-clip-text text-transparent">
              Solutions for Every Industry
            </h2>
            <p className="text-xl text-white/60 max-w-2xl mx-auto">
              Tailored AI analytics for your specific business needs
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {[
              {
                title: "Financial Services",
                description: "Real-time fraud detection, risk assessment, and compliance monitoring for banking and fintech",
                icon: TrendingUp,
                color: "from-green-500 to-emerald-500"
              },
              {
                title: "Healthcare",
                description: "Patient data analysis, predictive diagnostics, and HIPAA-compliant security measures",
                icon: Activity,
                color: "from-red-500 to-pink-500"
              },
              {
                title: "E-Commerce",
                description: "Customer behavior analytics, inventory forecasting, and personalized recommendations",
                icon: BarChart3,
                color: "from-purple-500 to-blue-500"
              },
            ].map((solution, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.1 }}
              >
                <Card className="p-8 bg-gradient-to-b from-white/5 to-transparent border-white/10 hover:border-white/20 transition-all h-full group">
                  <div className={`w-16 h-16 rounded-2xl bg-gradient-to-br ${solution.color} flex items-center justify-center mb-6 group-hover:scale-110 transition-transform`}>
                    <solution.icon className="w-8 h-8 text-white" />
                  </div>
                  <h3 className="text-2xl font-semibold text-white mb-4">{solution.title}</h3>
                  <p className="text-white/70 leading-relaxed">{solution.description}</p>
                </Card>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* About/Stats Section */}
      <section id="about" className="py-32 px-6 bg-gradient-to-b from-transparent via-purple-500/5 to-transparent">
        <div className="max-w-7xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-20"
          >
            <h2 className="text-5xl md:text-6xl font-bold mb-6 bg-gradient-to-r from-white to-white/60 bg-clip-text text-transparent">
              Trusted by Data Leaders
            </h2>
            <p className="text-xl text-white/60 max-w-2xl mx-auto">
              Join thousands of organizations that rely on Xplore for their data analytics
            </p>
          </motion.div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            {[
              { value: "50K+", label: "Active Users" },
              { value: "1B+", label: "Data Points Analyzed" },
              { value: "99.9%", label: "Uptime SLA" },
              { value: "24/7", label: "Expert Support" },
            ].map((stat, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, scale: 0.8 }}
                whileInView={{ opacity: 1, scale: 1 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.1 }}
                className="text-center"
              >
                <div className="text-5xl md:text-6xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent mb-2">
                  {stat.value}
                </div>
                <div className="text-white/60 text-lg">{stat.label}</div>
              </motion.div>
            ))}
          </div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="mt-20 text-center"
          >
            <Card className="p-12 bg-gradient-to-b from-white/5 to-transparent border-white/10 backdrop-blur-xl">
              <h3 className="text-3xl font-bold text-white mb-4">Ready to Transform Your Data?</h3>
              <p className="text-white/70 text-lg mb-8 max-w-2xl mx-auto">
                Start your free trial today and experience the power of AI-driven analytics
              </p>
              <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                <Link to="/signup">
                  <Button size="lg" className="bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white px-8 py-6 text-lg">
                    Start Free Trial
                    <ArrowRight className="ml-2 w-5 h-5" />
                  </Button>
                </Link>
                <Button size="lg" variant="outline" className="border-white/20 text-white hover:bg-white/5 px-8 py-6 text-lg">
                  Schedule Demo
                </Button>
              </div>
            </Card>
          </motion.div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-white/5 py-16 px-6">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-12 mb-12">
            <div>
              <div className="flex items-center gap-2 mb-4">
                <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
                  <Brain className="w-6 h-6 text-white" />
                </div>
                <span className="text-xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
                  Xplore
                </span>
              </div>
              <p className="text-white/60">
                Enterprise-grade AI analytics platform for the modern data team.
              </p>
            </div>

            <div>
              <h4 className="font-semibold text-white mb-4">Product</h4>
              <ul className="space-y-3 text-white/60">
                <li><a href="#features" className="hover:text-white transition-colors">Features</a></li>
                <li><a href="#demo" className="hover:text-white transition-colors">Security</a></li>
                <li><Link to="/signup" className="hover:text-white transition-colors">Get Started</Link></li>
              </ul>
            </div>

            <div>
              <h4 className="font-semibold text-white mb-4">Company</h4>
              <ul className="space-y-3 text-white/60">
                <li><a href="#about" className="hover:text-white transition-colors">About</a></li>
                <li><a href="#solutions" className="hover:text-white transition-colors">Solutions</a></li>
                <li><Link to="/login" className="hover:text-white transition-colors">Sign In</Link></li>
                <li><a href="mailto:contact@xplore.ai" className="hover:text-white transition-colors">Contact</a></li>
              </ul>
            </div>

            <div>
              <h4 className="font-semibold text-white mb-4">Legal</h4>
              <ul className="space-y-3 text-white/60">
                <li><span className="cursor-not-allowed opacity-50">Privacy Policy</span></li>
                <li><span className="cursor-not-allowed opacity-50">Terms of Service</span></li>
                <li><a href="#demo" className="hover:text-white transition-colors">Security</a></li>
                <li><span className="cursor-not-allowed opacity-50">Compliance</span></li>
              </ul>
            </div>
          </div>

          <div className="border-t border-white/5 pt-8 flex flex-col md:flex-row items-center justify-between gap-4">
            <p className="text-white/40">© 2026 Xplore. All rights reserved.</p>
            <div className="flex items-center gap-6">
              <a href="https://xplore.ai" target="_blank" rel="noopener noreferrer" className="text-white/40 hover:text-white transition-colors" aria-label="Visit website">
                <Globe className="w-5 h-5" />
              </a>
              <a href="https://twitter.com/xplore" target="_blank" rel="noopener noreferrer" className="text-white/40 hover:text-white transition-colors" aria-label="Follow on Twitter">
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M8.29 20.251c7.547 0 11.675-6.253 11.675-11.675 0-.178 0-.355-.012-.53A8.348 8.348 0 0022 5.92a8.19 8.19 0 01-2.357.646 4.118 4.118 0 001.804-2.27 8.224 8.224 0 01-2.605.996 4.107 4.107 0 00-6.993 3.743 11.65 11.65 0 01-8.457-4.287 4.106 4.106 0 001.27 5.477A4.072 4.072 0 012.8 9.713v.052a4.105 4.105 0 003.292 4.022 4.095 4.095 0 01-1.853.07 4.108 4.108 0 003.834 2.85A8.233 8.233 0 012 18.407a11.616 11.616 0 006.29 1.84" /></svg>
              </a>
              <a href="https://github.com/xplore" target="_blank" rel="noopener noreferrer" className="text-white/40 hover:text-white transition-colors" aria-label="View on GitHub">
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" /></svg>
              </a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
