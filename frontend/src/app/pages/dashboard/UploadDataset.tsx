import { motion } from "motion/react";
import { Upload, File, FileText, Database, CheckCircle2, AlertCircle, Clock } from "lucide-react";
import { Card } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Progress } from "../../components/ui/progress";
import { Badge } from "../../components/ui/badge";
import { useState } from "react";

const recentUploads = [
  { name: "Q1_Sales_2024.csv", size: "2.4 MB", status: "complete", date: "2 hours ago", rows: "15,234" },
  { name: "Customer_Data.xlsx", size: "5.1 MB", status: "processing", date: "5 hours ago", rows: "28,491" },
  { name: "Employee_Records.csv", size: "1.8 MB", status: "complete", date: "1 day ago", rows: "8,432" },
  { name: "Inventory_Log.json", size: "3.2 MB", status: "failed", date: "2 days ago", rows: "N/A" },
];

export default function UploadDataset() {
  const [dragActive, setDragActive] = useState(false);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave" || e.type === "drop") {
      setDragActive(false);
    }
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-4xl font-bold text-white mb-2">Upload Dataset</h1>
        <p className="text-white/60">Upload your data files for AI-powered analysis and insights</p>
      </div>

      {/* Upload Area */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <Card className="p-12 bg-gradient-to-b from-white/5 to-transparent border-white/10 relative overflow-hidden">
          <div
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrag}
            className={`border-2 border-dashed rounded-2xl p-16 text-center transition-all ${
              dragActive 
                ? "border-blue-500 bg-blue-500/10" 
                : "border-white/20 hover:border-blue-500/50 hover:bg-white/5"
            }`}
          >
            <motion.div
              animate={dragActive ? { scale: 1.1 } : { scale: 1 }}
              className="flex flex-col items-center"
            >
              <div className="w-24 h-24 rounded-2xl bg-gradient-to-br from-blue-500/20 to-purple-500/20 flex items-center justify-center mb-6">
                <Upload className="w-12 h-12 text-blue-400" />
              </div>
              
              <h3 className="text-2xl font-semibold text-white mb-2">
                {dragActive ? "Drop your files here" : "Drag & drop your files"}
              </h3>
              <p className="text-white/60 mb-6">or click to browse from your computer</p>
              
              <Button className="bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white mb-6">
                <Upload className="w-4 h-4 mr-2" />
                Choose Files
              </Button>

              <div className="flex flex-wrap items-center justify-center gap-4 text-sm text-white/60">
                <span className="flex items-center gap-1">
                  <FileText className="w-4 h-4" />
                  CSV, XLSX, JSON
                </span>
                <span>•</span>
                <span>Max 100MB per file</span>
                <span>•</span>
                <span>Multiple files supported</span>
              </div>
            </motion.div>
          </div>

          {/* Features */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-8">
            {[
              { icon: CheckCircle2, title: "Auto-Validation", description: "Automatic data quality checks" },
              { icon: Database, title: "Smart Processing", description: "AI-powered data profiling" },
              { icon: AlertCircle, title: "Secure Upload", description: "AES-256 encryption" },
            ].map((feature, index) => (
              <div key={index} className="flex items-start gap-3 p-4 rounded-lg bg-white/5">
                <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500/20 to-purple-500/20 flex items-center justify-center flex-shrink-0">
                  <feature.icon className="w-5 h-5 text-blue-400" />
                </div>
                <div>
                  <p className="text-white font-medium mb-1">{feature.title}</p>
                  <p className="text-white/60 text-sm">{feature.description}</p>
                </div>
              </div>
            ))}
          </div>
        </Card>
      </motion.div>

      {/* Recent Uploads */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
      >
        <Card className="p-6 bg-gradient-to-b from-white/5 to-transparent border-white/10">
          <div className="mb-6">
            <h3 className="text-xl font-semibold text-white mb-1">Recent Uploads</h3>
            <p className="text-white/60 text-sm">Your recently uploaded datasets</p>
          </div>

          <div className="space-y-3">
            {recentUploads.map((upload, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.3 + index * 0.1 }}
                className="flex items-center gap-4 p-4 rounded-lg bg-white/5 hover:bg-white/10 transition-all"
              >
                <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-blue-500/20 to-purple-500/20 flex items-center justify-center flex-shrink-0">
                  <File className="w-6 h-6 text-blue-400" />
                </div>

                <div className="flex-1 min-w-0">
                  <p className="text-white font-medium mb-1">{upload.name}</p>
                  <div className="flex items-center gap-4 text-sm text-white/60">
                    <span>{upload.size}</span>
                    <span>•</span>
                    <span>{upload.rows} rows</span>
                    <span>•</span>
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {upload.date}
                    </span>
                  </div>
                </div>

                <Badge className={
                  upload.status === "complete" ? "bg-green-500/10 text-green-400 border-green-500/20" :
                  upload.status === "processing" ? "bg-blue-500/10 text-blue-400 border-blue-500/20" :
                  "bg-red-500/10 text-red-400 border-red-500/20"
                }>
                  {upload.status === "complete" && <CheckCircle2 className="w-3 h-3 mr-1" />}
                  {upload.status.charAt(0).toUpperCase() + upload.status.slice(1)}
                </Badge>

                {upload.status === "processing" && (
                  <div className="w-32">
                    <Progress value={65} className="h-2" />
                  </div>
                )}

                <Button variant="ghost" size="sm" className="text-white/60 hover:text-white">
                  View Details
                </Button>
              </motion.div>
            ))}
          </div>
        </Card>
      </motion.div>
    </div>
  );
}
