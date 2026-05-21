import { motion } from "motion/react";
import { User, Lock, Bell, Key, Shield, Globe } from "lucide-react";
import { Card } from "../../components/ui/card";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Button } from "../../components/ui/button";
import { Switch } from "../../components/ui/switch";

export default function Settings() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-4xl font-bold text-white mb-2">Settings</h1>
        <p className="text-white/60">Manage your account and preferences</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Settings Menu */}
        <Card className="p-6 bg-gradient-to-b from-white/5 to-transparent border-white/10 h-fit">
          <div className="space-y-2">
            {[
              { icon: User, label: "Profile" },
              { icon: Lock, label: "Security" },
              { icon: Bell, label: "Notifications" },
              { icon: Key, label: "API Keys" },
              { icon: Shield, label: "Privacy" },
              { icon: Globe, label: "Integrations" },
            ].map((item, index) => (
              <button
                key={index}
                className="w-full flex items-center gap-3 px-4 py-3 rounded-lg text-white/80 hover:text-white hover:bg-white/5 transition-all"
              >
                <item.icon className="w-5 h-5" />
                <span>{item.label}</span>
              </button>
            ))}
          </div>
        </Card>

        {/* Settings Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Profile Settings */}
          <Card className="p-6 bg-gradient-to-b from-white/5 to-transparent border-white/10">
            <h3 className="text-xl font-semibold text-white mb-6">Profile Settings</h3>
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="text-white mb-2">First Name</Label>
                  <Input defaultValue="John" className="bg-white/5 border-white/10 text-white" />
                </div>
                <div>
                  <Label className="text-white mb-2">Last Name</Label>
                  <Input defaultValue="Doe" className="bg-white/5 border-white/10 text-white" />
                </div>
              </div>
              <div>
                <Label className="text-white mb-2">Email</Label>
                <Input defaultValue="john@company.com" className="bg-white/5 border-white/10 text-white" />
              </div>
              <div>
                <Label className="text-white mb-2">Company</Label>
                <Input defaultValue="Acme Inc." className="bg-white/5 border-white/10 text-white" />
              </div>
              <Button className="bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white">
                Save Changes
              </Button>
            </div>
          </Card>

          {/* Security Settings */}
          <Card className="p-6 bg-gradient-to-b from-white/5 to-transparent border-white/10">
            <h3 className="text-xl font-semibold text-white mb-6">Security</h3>
            <div className="space-y-4">
              <div className="flex items-center justify-between p-4 rounded-lg bg-white/5">
                <div>
                  <p className="text-white font-medium">Two-Factor Authentication</p>
                  <p className="text-white/60 text-sm">Add an extra layer of security</p>
                </div>
                <Switch />
              </div>
              <div className="flex items-center justify-between p-4 rounded-lg bg-white/5">
                <div>
                  <p className="text-white font-medium">Session Timeout</p>
                  <p className="text-white/60 text-sm">Automatically log out after inactivity</p>
                </div>
                <Switch defaultChecked />
              </div>
              <div className="flex items-center justify-between p-4 rounded-lg bg-white/5">
                <div>
                  <p className="text-white font-medium">Login Notifications</p>
                  <p className="text-white/60 text-sm">Get notified of new login attempts</p>
                </div>
                <Switch defaultChecked />
              </div>
            </div>
          </Card>

          {/* Notification Settings */}
          <Card className="p-6 bg-gradient-to-b from-white/5 to-transparent border-white/10">
            <h3 className="text-xl font-semibold text-white mb-6">Notifications</h3>
            <div className="space-y-4">
              <div className="flex items-center justify-between p-4 rounded-lg bg-white/5">
                <div>
                  <p className="text-white font-medium">Security Alerts</p>
                  <p className="text-white/60 text-sm">Receive alerts about security threats</p>
                </div>
                <Switch defaultChecked />
              </div>
              <div className="flex items-center justify-between p-4 rounded-lg bg-white/5">
                <div>
                  <p className="text-white font-medium">Data Processing</p>
                  <p className="text-white/60 text-sm">Notify when datasets are processed</p>
                </div>
                <Switch defaultChecked />
              </div>
              <div className="flex items-center justify-between p-4 rounded-lg bg-white/5">
                <div>
                  <p className="text-white font-medium">Weekly Reports</p>
                  <p className="text-white/60 text-sm">Get weekly summary reports</p>
                </div>
                <Switch />
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
