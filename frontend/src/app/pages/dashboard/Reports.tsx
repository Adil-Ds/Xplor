import { motion } from "motion/react";
import { FileText, Download, Calendar } from "lucide-react";
import { Card } from "../../components/ui/card";
import { Button } from "../../components/ui/button";

const reports = [
  { name: "Q1 Security Analysis", date: "Jan 15, 2024", type: "PDF", size: "2.4 MB" },
  { name: "Data Quality Report", date: "Jan 12, 2024", type: "PDF", size: "1.8 MB" },
  { name: "Monthly Analytics", date: "Jan 10, 2024", type: "XLSX", size: "3.2 MB" },
  { name: "Risk Assessment", date: "Jan 8, 2024", type: "PDF", size: "2.1 MB" },
];

export default function Reports() {
  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-bold text-white mb-2">Reports</h1>
          <p className="text-white/60">Generate and download AI-powered reports</p>
        </div>
        <Button className="bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white">
          <FileText className="w-4 h-4 mr-2" />
          Generate New Report
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {reports.map((report, index) => (
          <motion.div key={index} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: index * 0.1 }}>
            <Card className="p-6 bg-gradient-to-b from-white/5 to-transparent border-white/10 hover:border-white/20 transition-all">
              <div className="flex items-start gap-4">
                <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-blue-500/20 to-purple-500/20 flex items-center justify-center flex-shrink-0">
                  <FileText className="w-6 h-6 text-blue-400" />
                </div>
                <div className="flex-1">
                  <h3 className="text-white font-semibold mb-2">{report.name}</h3>
                  <div className="flex items-center gap-4 text-sm text-white/60 mb-4">
                    <span className="flex items-center gap-1">
                      <Calendar className="w-3 h-3" />
                      {report.date}
                    </span>
                    <span>{report.type}</span>
                    <span>{report.size}</span>
                  </div>
                  <Button variant="outline" size="sm" className="border-white/10 bg-white/5 text-white hover:bg-white/10">
                    <Download className="w-4 h-4 mr-2" />
                    Download
                  </Button>
                </div>
              </div>
            </Card>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
