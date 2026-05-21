import { createBrowserRouter } from "react-router";
import LandingPage from "./pages/LandingPage";
import LoginPage from "./pages/LoginPage";
import SignupPage from "./pages/SignupPage";
import MFAPage from "./pages/MFAPage";
import ForgotPasswordPage from "./pages/ForgotPasswordPage";
import DashboardLayout from "./layouts/DashboardLayout";
import Overview from "./pages/dashboard/Overview";
import UploadDataset from "./pages/dashboard/UploadDataset";
import AICleaning from "./pages/dashboard/AICleaning";
import Analytics from "./pages/dashboard/Analytics";
import Forecasting from "./pages/dashboard/Forecasting";
import RiskEngine from "./pages/dashboard/RiskEngine";
import SecurityCenter from "./pages/dashboard/SecurityCenter";
import AIChat from "./pages/dashboard/AIChat";
import Reports from "./pages/dashboard/Reports";
import Settings from "./pages/dashboard/Settings";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <LandingPage />,
  },
  {
    path: "/login",
    element: <LoginPage />,
  },
  {
    path: "/signup",
    element: <SignupPage />,
  },
  {
    path: "/mfa",
    element: <MFAPage />,
  },
  {
    path: "/forgot-password",
    element: <ForgotPasswordPage />,
  },
  {
    path: "/dashboard",
    element: <DashboardLayout />,
    children: [
      {
        index: true,
        element: <Overview />,
      },
      {
        path: "upload",
        element: <UploadDataset />,
      },
      {
        path: "ai-cleaning",
        element: <AICleaning />,
      },
      {
        path: "analytics",
        element: <Analytics />,
      },
      {
        path: "forecasting",
        element: <Forecasting />,
      },
      {
        path: "risk-engine",
        element: <RiskEngine />,
      },
      {
        path: "security",
        element: <SecurityCenter />,
      },
      {
        path: "ai-chat",
        element: <AIChat />,
      },
      {
        path: "reports",
        element: <Reports />,
      },
      {
        path: "settings",
        element: <Settings />,
      },
    ],
  },
]);
